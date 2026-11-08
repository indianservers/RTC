"""One validated pagination/search implementation for existing admin reads."""

from fastapi.encoders import jsonable_encoder
from sqlalchemy import String, func, or_, select


def list_records(
    session, model, limit, offset, q="", sort_by="id", descending=False, active=None, scope=None
):
    if sort_by not in model.__table__.columns:
        raise ValueError("Unknown sort column")
    query = select(model)
    if scope is not None:
        query=query.where(scope)
    if active is not None:
        query = query.where(model.active.is_(active))
    if q:
        columns = [c for c in model.__table__.columns if isinstance(c.type, String)]
        query = query.where(
            or_(
                *(
                    func.lower(c).contains(q.casefold(), autoescape=True)
                    for c in columns
                )
            )
        )
    count = session.scalar(select(func.count()).select_from(query.subquery()))
    column = model.__table__.c[sort_by]
    query = (
        query.order_by(
            column.desc() if descending else column.asc(), model.__table__.c.id
        )
        .offset(offset)
        .limit(limit)
    )
    return {
        "data": jsonable_encoder(list(session.scalars(query))),
        "limit": limit,
        "offset": offset,
        "total": count,
    }
