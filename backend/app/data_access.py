"""Local bearer capabilities backed by the existing user/role/grant tables."""

import hashlib
import os
import secrets
from dataclasses import dataclass

from fastapi import HTTPException
from sqlalchemy import exists, false, select, true
from sqlalchemy.orm import Session

from . import catalog, operations, records
from .domain import Category, Operator, Route, Service
from .schema1a import AdminRole, AdminUser, AdminUserRole


@dataclass(frozen=True)
class Principal:
    username: str
    role: str
    operators: tuple[str, ...] = ()
    global_scope: bool = False
    station_grants: tuple[tuple[str | None, str | None], ...] = ()

    @property
    def root(self):
        return self.role == "ADMIN"

    def require(self, action):
        if action in {"approve", "publish", "rollback"} and self.role not in {
            "ADMIN",
            "APPROVER",
        }:
            raise HTTPException(403, "An authorized approver is required")
        if action == "edit" and self.role not in {"ADMIN", "EDITOR"}:
            raise HTTPException(403, "An authorized data editor is required")


def authenticate(engine, authorization):
    supplied = (authorization or "").removeprefix("Bearer ")
    root = os.getenv("RTC_ADMIN_TOKEN")
    if root and secrets.compare_digest(supplied, root):
        return Principal("local-administrator", "ADMIN")
    if not supplied:
        raise HTTPException(401, "Administrator credentials required")
    digest = "token:" + hashlib.sha256(supplied.encode()).hexdigest()
    with Session(engine) as session:
        user = session.scalar(
            select(AdminUser).where(
                AdminUser.password_hash == digest, AdminUser.active.is_(True)
            )
        )
        if user:
            grants = list(
                session.execute(
                    select(
                        AdminRole.role_code,
                        AdminUserRole.operator_id,
                        AdminUserRole.station_id,
                    )
                    .join(AdminUserRole, AdminUserRole.role_id == AdminRole.id)
                    .where(
                        AdminUserRole.user_id == user.id,
                        AdminUserRole.active.is_(True),
                        AdminRole.active.is_(True),
                    )
                )
            )
            roles = {r[0] for r in grants}
            if len(roles) == 1 and roles <= {
                "EDITOR",
                "APPROVER",
                "OPERATIONS_VIEWER",
                "DISPATCHER",
                "STATION_SUPERVISOR",
                "OPERATOR_ADMIN",
            }:
                return Principal(
                    user.username,
                    next(iter(roles)),
                    tuple(r[1] for r in grants if r[1]),
                    any(r[1] is None for r in grants)
                    and next(iter(roles)) == "APPROVER",
                    tuple((r[1], r[2]) for r in grants),
                )
    raise HTTPException(401, "Invalid local administrator credentials")


PARENTS = {
    "service_id": Service,
    "trip_id": operations.Trip,
    "route_id": Route,
    "variant_id": catalog.Variant,
    "route_variant_id": catalog.Variant,
    "category_id": Category,
    "table_id": records.FareTable,
    "division_id": catalog.Division,
    "vehicle_id": catalog.Vehicle,
    "concession_id": catalog.Concession,
    "source_id": operations.DataSource,
    "stop_id": __import__("app.domain", fromlist=["Stop"]).Stop,
}
SHARED = {
    "stations",
    "station-aliases",
    "states",
    "districts",
    "cities",
    "bays",
    "vehicle-types",
    "seat-layouts",
}


def scope_condition(model, operators, seen=()):
    if model in seen:
        return false()
    if model is Operator:
        return model.id.in_(operators)
    if "operator_id" in model.__table__.columns:
        return model.operator_id.in_(operators)
    for name, parent in PARENTS.items():
        if name in model.__table__.columns:
            return exists(
                select(parent.id).where(
                    parent.id == getattr(model, name),
                    scope_condition(parent, operators, (*seen, model)),
                )
            )
    return false()


def read_scope(resource, model, principal, operator_id=None):
    if not (principal.root or principal.global_scope):
        if operator_id and operator_id not in principal.operators:
            raise HTTPException(403, "Operator is outside your authorization")
        if resource in SHARED:
            return true()
        return scope_condition(
            model, (operator_id,) if operator_id else principal.operators
        )
    return (
        scope_condition(model, (operator_id,))
        if operator_id and resource not in SHARED
        else true()
    )


def owner(session, model, values, seen=()):
    if model in seen:
        return None
    if model is Operator:
        return values.get("id")
    if values.get("operator_id"):
        return values["operator_id"]
    for name, parent in PARENTS.items():
        if values.get(name):
            row = session.get(parent, values[name])
            if row:
                return owner(
                    session,
                    parent,
                    {c.name: getattr(row, c.name) for c in parent.__table__.columns},
                    (*seen, model),
                )
    return None


def authorize_record(session, resource, model, values, principal, operator_id=None):
    if resource == "data-sources" and values.get("is_official") and not principal.root:
        raise HTTPException(
            403, "Only a global administrator may attest an official source"
        )
    record_owner = owner(session, model, values)
    if record_owner:
        for name, parent in PARENTS.items():
            if values.get(name):
                reference = session.get(parent, values[name])
                reference_owner = (
                    owner(
                        session,
                        parent,
                        {
                            c.name: getattr(reference, c.name)
                            for c in parent.__table__.columns
                        },
                    )
                    if reference
                    else None
                )
                if reference_owner and reference_owner != record_owner:
                    raise HTTPException(
                        403, "Cross-operator reference is not permitted: " + name
                    )
    if operator_id and record_owner and operator_id != record_owner:
        raise HTTPException(403, "Record belongs to another operator")
    if not (principal.root or principal.global_scope) and (
        resource in SHARED
        or not record_owner
        or record_owner not in principal.operators
    ):
        raise HTTPException(
            403, "Shared or other-operator records require a global administrator"
        )
    return record_owner
