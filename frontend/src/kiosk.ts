export function kioskIdleMinutes() {
  const value = Number(sessionStorage.getItem("rtc-kiosk-idle") || 15);
  return [2, 5, 10, 15].includes(value) ? value : 15;
}
