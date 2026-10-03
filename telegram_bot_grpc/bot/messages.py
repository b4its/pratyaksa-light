"""Message builders and keyboards (pure functions — no I/O, easy to test)."""

from __future__ import annotations

from typing import Any


def esc(s: str) -> str:
    """HTML-escape a string for Telegram ``parse_mode=HTML``."""
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def normalize_base(raw: str) -> str:
    """Normalise the WO link base URL (mirrors the Rust helper)."""
    t = (raw or "").strip().rstrip("/")
    if not t:
        return "http://localhost"
    if t.startswith("http://") or t.startswith("https://"):
        return t
    return f"https://{t}"


def build_alert_message(d: dict[str, str], wo_base: str) -> str:
    base = normalize_base(wo_base)
    wo_link = f"{base}/wo/create/{esc(d.get('asset_id', ''))}"
    return (
        "🚨 <b>[URGENT ALARM : PRATYAKSA]</b> 🚨\n\n"
        f"🚜 <b>Unit:</b> {esc(d.get('asset_id', ''))} ({esc(d.get('model', ''))})\n"
        f"📍 <b>Lokasi:</b> {esc(d.get('lokasi', ''))}\n"
        f"⚠️ <b>Status:</b> {esc(d.get('status', ''))} (Estimasi Sisa Umur: {esc(d.get('rul', ''))} Jam)\n\n"
        "🔍 <b>Analisis Kerusakan AI (SHAP):</b>\n"
        f"1. {esc(d.get('shap1', ''))}\n"
        f"2. {esc(d.get('shap2', ''))}\n\n"
        "🛠️ <b>Rekomendasi Tindakan:</b>\n"
        "Arahkan unit ke Workshop Pit terdekat sebelum breakdown.\n\n"
        "📦 <b>Info Suku Cadang:</b>\n"
        f"- Part Name: {esc(d.get('part_name', ''))}\n"
        f"- Part No: {esc(d.get('part_no', ''))}\n"
        f"- Stok Workshop: {esc(d.get('stok', ''))} Unit\n\n"
        f'🔗 <a href="{wo_link}">Buat Work Order</a>'
    )


def greeting_message() -> str:
    return (
        "⚡️ <b>SYSTEM ONLINE: PRATYAKSA Command Center</b> ⚡️\n"
        "<i>Engineered by Oryphem</i>\n\n"
        "Selamat datang! Anda telah terhubung dengan asisten Predictive Maintenance berbasis AI.\n\n"
        "Tujuan utama: <b>Zero Breakdown</b>, meminimalisir Unplanned Downtime, dan memaksimalkan profit operasional tambang Anda. 📈💰\n\n"
        "<b>Kapabilitas Sistem:</b>\n"
        "📡 Real-time Telemetry — memantau sensor unit 24/7\n"
        "🧠 Smart Diagnostics (SHAP) — ungkap akar masalah sebelum breakdown\n"
        "🛠️ CMMS Ready — eskalasi alarm jadi Work Order 1 klik\n\n"
        "Silakan pilih jenis laporan di bawah ini:"
    )


def start_menu_keyboard() -> list[list[dict[str, str]]]:
    return [
        [{"text": "📊 Laporan Realtime", "callback_data": "/status"}],
        [{"text": "📋 Laporan Realtime + Detail Data", "callback_data": "/detail"}],
        [{"text": "🤖 Status Pratyaksa", "callback_data": "/pratyaksa"}],
        [{"text": "Matikan Notifikasi Pratyaksa", "callback_data": "/down"}],
    ]


def build_fleet_summary(data: dict[str, Any]) -> str:
    return (
        "📊 <b>PRATYAKSA Fleet Status</b>\n\n"
        f"🔴 CRITICAL : {data.get('critical', 0)} unit\n"
        f"🟡 WARNING  : {data.get('warning', 0)} unit\n"
        f"🟢 NORMAL   : {data.get('normal', 0)} unit\n"
        f"⚫ RUSAK    : {data.get('rusak', 0)} unit\n"
        "─────────────────\n"
        f"📦 Total Unit : {data.get('total', 0)} unit\n\n"
        "<i>Data real-time dari backend PRATYAKSA.</i>"
    )


def build_pratyaksa_status(data: dict[str, Any]) -> str:
    mode = data.get("mode", "simulasi")
    fleet = data.get("fleet_count", 0)
    health = data.get("last_health_check") or "-"
    poll = data.get("last_fleet_poll") or "-"
    return (
        "🤖 <b>PRATYAKSA Status</b>\n\n"
        f"🟡 Mode       : <b>{mode}</b>\n"
        f"📦 Fleet Count : {fleet} unit\n"
        f"🩺 Health Check : {health}\n"
        f"📡 Fleet Poll   : {poll}\n\n"
        "<i>Mode simulasi — data dihasilkan engine Python internal (tanpa koneksi eksternal).</i>"
    )


def build_unit_detail(mode: str, d: dict[str, Any]) -> str:
    risk_level = d.get("risk_level", "UNKNOWN")
    lstm_rul = float(d.get("lstm_rul_hours", 0.0) or 0.0)
    uncertainty = float(d.get("rul_uncertainty", 0.0) or 0.0)
    model_agreement = bool(d.get("model_agreement", False))
    drift = bool((d.get("drift_status") or {}).get("drift_detected", False))
    twin = d.get("digital_twin") or {}
    brake_twin = float(twin.get("brake_twin_rul", 0.0) or 0.0)
    hydraulic_twin = float(twin.get("hydraulic_twin_rul", 0.0) or 0.0)

    risk_icon = {"CRITICAL": "🔴", "WARNING": "🟡", "NORMAL": "🟢"}.get(risk_level, "⚪")

    return (
        f"🚜 <b>UNIT DETAIL: {d.get('asset_id', 'N/A')}</b>\n\n"
        f"🟡 <b>Sumber Data:</b> {mode}\n\n"
        f"📍 <b>Tipe:</b> {d.get('equipment_type', 'N/A')}\n"
        f"{risk_icon} <b>Risk Level:</b> {risk_level}\n"
        f"🕒 <b>RUL:</b> {lstm_rul:.0f} jam\n"
        f"📊 <b>Uncertainty:</b> {uncertainty:.1f}\n"
        f"🔄 <b>Model Agreement:</b> {model_agreement}\n"
        f"⚠️ <b>Drift Detected:</b> {drift}\n\n"
        "💡 <b>Digital Twin Prediction:</b>\n"
        f"• Brake Twin: {brake_twin:.0f} jam\n"
        f"• Hydraulic Twin: {hydraulic_twin:.0f} jam\n\n"
        f"⏰ <b>Last processed:</b> {format_processed_at(d.get('processed_at'))}\n\n"
        f"<i>Data sinkron dengan website — mode: {mode}.</i>"
    )


def format_processed_at(value: Any) -> str:
    """Format an epoch-seconds ``processed_at`` as ``YYYY-MM-DD HH:MM:SS UTC``.

    Mirrors the Rust ``/unit`` handler which converted the epoch to a UTC wall
    clock (its own arithmetic, reproduced here for 1:1 output parity). Returns
    ``"N/A"`` when the value is missing or non-positive.
    """
    try:
        ts = float(value or 0.0)
    except (TypeError, ValueError):
        ts = 0.0
    if ts <= 0.0:
        return "N/A"
    secs = int(ts)
    days = secs // 86400
    hours = (secs % 86400) // 3600
    minutes = (secs % 3600) // 60
    secs_remain = secs % 60
    return (
        f"{1970 + days // 365}-{(days % 365) // 30 + 1:02d}-{days % 30 + 1:02d} "
        f"{hours:02d}:{minutes:02d}:{secs_remain:02d} UTC"
    )


def build_detail_report(
    fleet_summary: str,
    mode: str,
    avg_rul: float,
    fleet: list[dict[str, Any]],
) -> str:
    unit_lines = ""
    for i, unit in enumerate(fleet):
        if i >= 10:
            break
        rid = unit.get("asset_id", "?")
        eq = unit.get("equipment_type", "?")
        risk = unit.get("risk_level", "?")
        rul = float(unit.get("lstm_rul_hours", 0.0) or 0.0)
        drift = bool(unit.get("drift_detected", False))
        agreement = bool(unit.get("model_agreement", True))
        risk_icon = {"CRITICAL": "🔴", "WARNING": "🟡", "NORMAL": "🟢"}.get(risk, "⚪")
        drift_icon = "⚠️" if drift else "✅"
        agree_icon = "✅" if agreement else "⚠️"
        unit_lines += (
            f"{risk_icon} <b>{rid}</b> ({eq})\n"
            f"┃   Risk: {risk} | RUL: {rul:.0f} jam\n"
            f"┃   Drift: {drift_icon} | Model: {agree_icon}\n"
        )

    mode_icon = "🟡"
    first_rul = float(fleet[0].get("lstm_rul_hours", 500.0) or 500.0) if fleet else 500.0

    return (
        f"{fleet_summary}\n\n"
        "─────────────────\n\n"
        "🧠 <b>ANALISA KERUSAKAN — DETAIL</b>\n\n"
        f"{mode_icon} <b>Sumber Data:</b> {mode}\n"
        f"📊 <b>Rata-rata RUL:</b> {avg_rul:.0f} jam\n"
        f"📋 <b>Unit terpantau:</b> {len(fleet)} unit\n\n"
        "── <b>Daftar Unit</b> ──\n\n"
        f"{unit_lines}\n"
        "── <b>Parameter Lingkungan & Operasional</b> ──\n"
        "🌡️  Suhu Ambient: 32-42°C\n"
        "💧 Kelembaban: 65-85%\n"
        "💨 Kecepatan Angin: 2-8 m/s\n"
        "🛣️  Grade Jalan: 6-12%\n"
        "📏 Jarak Angkut: 1.5-3.2 km\n\n"
        "── <b>Prediksi AI</b> ──\n"
        "🧬 Model: XGBoost (klasifikasi) + LSTM (RUL)\n"
        "📈 Akurasi: 94.2% (ensemble)\n"
        "🔄 Auto-retrain: Setiap 24 jam\n"
        "🛡️ Drift Detection: Real-time (Z-score)\n\n"
        "── <b>Komponen dengan RUL Terendah</b> ──\n"
        f"🔧 Hydraulic System: ~{first_rul * 0.7:.0f} jam\n"
        f"🔧 Brake System: ~{first_rul * 0.35:.0f} jam\n"
        f"🔧 Steering System: ~{first_rul * 0.6:.0f} jam\n\n"
        "── <b>SHAP — Faktor Penyebab Utama</b> ──\n"
        "1️⃣ payload_tonnage_t (beban berlebih)\n"
        "2️⃣ hour_meter_h (usia pakai)\n"
        "3️⃣ vibration_z_g (getaran abnormal)\n"
        "4️⃣ coolant_temp_c (overheating)\n"
        "5️⃣ oil_particle_count_iso (kontaminasi oli)\n\n"
        "<i>Data diperbaharui tiap 5 detik. Hubungi tim maintenance untuk tindakan lanjut.</i>"
    )
