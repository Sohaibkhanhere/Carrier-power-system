"""Export endpoint — downloads filtered data as .xlsx with multiple sheet types."""

from datetime import date
from io import BytesIO
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
import pandas as pd

from app.database import get_db
from app import models
from app.services.prediction import predict_prb

router = APIRouter(prefix="/api/export", tags=["export"])


@router.get("/kpi")
def export_kpi(
    date_from: date = Query(None),
    date_to: date = Query(None),
    tower: str = Query(None),
    carrier: str = Query(None),
    db: Session = Depends(get_db),
):
    q = (
        db.query(
            models.Carrier.sector_label,
            models.Carrier.cell_name,
            models.Tower.tower_label,
            models.KpiHourly.date,
            models.KpiHourly.hour,
            models.KpiHourly.traffic_users,
            models.KpiHourly.prb_utilization,
            models.KpiHourly.power_watts,
            models.KpiHourly.source,
        )
        .join(models.Carrier, models.KpiHourly.carrier_id == models.Carrier.id)
        .join(models.Tower, models.Carrier.tower_id == models.Tower.id)
    )
    if date_from:
        q = q.filter(models.KpiHourly.date >= date_from)
    if date_to:
        q = q.filter(models.KpiHourly.date <= date_to)
    if tower:
        q = q.filter(models.Tower.tower_label == tower)
    if carrier:
        q = q.filter(models.Carrier.sector_label == carrier)

    rows = q.order_by(models.KpiHourly.date, models.KpiHourly.hour).all()

    df = pd.DataFrame([
        {
            "Carrier": r.sector_label,
            "Cell Name": r.cell_name,
            "Tower": r.tower_label,
            "Date": str(r.date),
            "Hour": r.hour,
            "Traffic Users": r.traffic_users,
            "PRB Utilization %": r.prb_utilization,
            "Power Watts": round(r.power_watts, 2) if r.power_watts else 0,
            "Source": r.source,
        }
        for r in rows
    ])

    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="KPI Data")

    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=kpi_export.xlsx"},
    )


@router.get("/decisions")
def export_decisions(
    date_from: date = Query(None),
    date_to: date = Query(None),
    tower: str = Query(None),
    db: Session = Depends(get_db),
):
    q = (
        db.query(
            models.Tower.tower_label,
            models.Decision.date,
            models.Decision.hour,
            models.Decision.mode,
            models.Decision.carrier_b_state,
            models.Decision.carrier_c_state,
            models.Decision.predicted_prb_used,
            models.Decision.power_watts,
        )
        .join(models.Tower, models.Decision.tower_id == models.Tower.id)
    )
    if date_from:
        q = q.filter(models.Decision.date >= date_from)
    if date_to:
        q = q.filter(models.Decision.date <= date_to)
    if tower:
        q = q.filter(models.Tower.tower_label == tower)

    rows = q.order_by(models.Decision.date, models.Decision.hour).all()

    df = pd.DataFrame([
        {
            "Tower": r.tower_label,
            "Date": str(r.date),
            "Hour": r.hour,
            "Mode": r.mode,
            "Carrier B": r.carrier_b_state,
            "Carrier C": r.carrier_c_state,
            "Avg Predicted PRB %": r.predicted_prb_used,
            "Power Watts": round(r.power_watts, 2) if r.power_watts else 0,
        }
        for r in rows
    ])

    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Decisions")

    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=decisions_export.xlsx"},
    )


@router.get("/explainability")
def export_explainability(
    carrier: str = Query(...),
    target_date: date = Query(...),
    target_hour: int = Query(...),
    db: Session = Depends(get_db),
):
    """Export the explainability breakdown for a prediction as .xlsx."""
    carrier_obj = db.query(models.Carrier).filter_by(sector_label=carrier).first()
    if not carrier_obj:
        return {"error": "Carrier not found"}

    pred = predict_prb(carrier_obj.id, target_date, target_hour, db)
    contributing = pred.get("contributing_dates", [])

    df = pd.DataFrame(contributing)
    if df.empty:
        df = pd.DataFrame(columns=["date", "weekday", "traffic_users", "prb_utilization", "power_watts", "source"])

    # Rename columns for clarity
    df.columns = ["Date", "Weekday", "Traffic Users", "PRB Utilization %", "Power Watts", "Source"]

    # Add summary row
    summary = pd.DataFrame([{
        "Date": f"PREDICTED (avg of {pred['sample_count']} samples)",
        "Weekday": "",
        "Traffic Users": pred["predicted_traffic"],
        "PRB Utilization %": pred["predicted_prb"],
        "Power Watts": "",
        "Source": f"Range: {pred['prb_min']}-{pred['prb_max']}%, StdDev: {pred['prb_std']}",
    }])
    df = pd.concat([df, summary], ignore_index=True)

    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Explainability")

    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=explainability_export.xlsx"},
    )


@router.get("/power-energy")
def export_power_energy(
    date_from: date = Query(None),
    date_to: date = Query(None),
    tower: str = Query(None),
    db: Session = Depends(get_db),
):
    """Export power/energy summary: Watts/kWh saved per day per tower."""
    from app.services.power import get_power_config, compute_tower_power
    from sqlalchemy import func as sqlfunc

    pconfig = get_power_config(db)

    # Query decisions
    q = (
        db.query(
            models.Tower.tower_label,
            models.Decision.date,
            models.Decision.hour,
            models.Decision.carrier_b_state,
            models.Decision.carrier_c_state,
            models.Decision.predicted_prb_used,
        )
        .join(models.Tower, models.Decision.tower_id == models.Tower.id)
    )
    if date_from:
        q = q.filter(models.Decision.date >= date_from)
    if date_to:
        q = q.filter(models.Decision.date <= date_to)
    if tower:
        q = q.filter(models.Tower.tower_label == tower)

    rows = q.order_by(models.Tower.tower_label, models.Decision.date, models.Decision.hour).all()

    # Compute per-row power
    all_on_power = compute_tower_power(True, True, True, 50, 50, 50, pconfig)
    records = []
    for r in rows:
        cb_on = r.carrier_b_state == "ON"
        cc_on = r.carrier_c_state == "ON"
        prb_b = r.predicted_prb_used or 50
        actual_power = compute_tower_power(True, cb_on, cc_on, 50, prb_b, prb_b, pconfig)
        saved = all_on_power - actual_power
        records.append({
            "Tower": r.tower_label,
            "Date": str(r.date),
            "Hour": r.hour,
            "Mode": "ON" if cb_on and cc_on else ("OFF" if not cb_on and not cc_on else "Mixed"),
            "Power Watts (Actual)": round(actual_power, 2),
            "Power Watts (All ON)": round(all_on_power, 2),
            "Power Saved Watts": round(saved, 2),
        })

    df_detail = pd.DataFrame(records)

    # Aggregate by day+tower
    if not df_detail.empty:
        df_detail["kWh"] = df_detail["Power Watts (Actual)"] / 1000
        df_detail["kWh Saved"] = df_detail["Power Saved Watts"] / 1000
        df_summary = (
            df_detail.groupby(["Tower", "Date"])
            .agg({
                "kWh": "sum",
                "kWh Saved": "sum",
                "Power Watts (Actual)": "mean",
                "Power Saved Watts": "mean",
            })
            .reset_index()
        )
        df_summary.columns = ["Tower", "Date", "Total kWh", "Total kWh Saved", "Avg Watts", "Avg Watts Saved"]
        df_summary["Total kWh"] = df_summary["Total kWh"].round(3)
        df_summary["Total kWh Saved"] = df_summary["Total kWh Saved"].round(3)
        df_summary["Avg Watts"] = df_summary["Avg Watts"].round(1)
        df_summary["Avg Watts Saved"] = df_summary["Avg Watts Saved"].round(1)
    else:
        df_summary = pd.DataFrame(columns=["Tower", "Date", "Total kWh", "Total kWh Saved", "Avg Watts", "Avg Watts Saved"])

    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df_summary.to_excel(writer, index=False, sheet_name="Daily Summary")
        df_detail.to_excel(writer, index=False, sheet_name="Hourly Detail")

    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=power_energy_export.xlsx"},
    )


@router.get("/thesis-report")
def export_thesis_report(db: Session = Depends(get_db)):
    """Comprehensive thesis report with multiple sheets:
    1. Site Overview — site/carrier structure
    2. Data Summary — date range, row counts, source breakdown
    3. Power Model — current config, watts per carrier
    4. Capacity Config — ceiling, bands
    5. Decision Statistics — mode distribution, energy savings
    6. Model Accuracy — training runs with MAE/RMSE
    7. Daily Energy — day-by-day actual vs baseline kWh
    """
    from app.services.power import get_power_config, compute_tower_power, compute_max_tower_power

    pconfig = get_power_config(db)

    # Sheet 1: Site Overview
    sites = db.query(models.Site).all()
    towers = db.query(models.Tower).all()
    carriers = db.query(models.Carrier).all()

    site_rows = []
    for site in sites:
        for tower in site.towers:
            for carrier in tower.carriers:
                site_rows.append({
                    "Site": site.enodeb_name,
                    "Tower": tower.tower_label,
                    "Carrier": carrier.sector_label,
                    "Cell Name": carrier.cell_name,
                    "Primary": "Yes" if carrier.is_primary else "No",
                    "Activation Order": carrier.activation_order,
                })
    df_site = pd.DataFrame(site_rows)

    # Sheet 2: Data Summary
    total_rows = db.query(models.KpiHourly).count()
    date_range = db.query(
        func.min(models.KpiHourly.date), func.max(models.KpiHourly.date)
    ).first()
    source_breakdown = (
        db.query(models.KpiHourly.source, func.count(models.KpiHourly.id))
        .group_by(models.KpiHourly.source)
        .all()
    )

    summary_rows = [{"Metric": "Total KPI Rows", "Value": total_rows}]
    summary_rows.append({"Metric": "Date Range Start", "Value": str(date_range[0]) if date_range[0] else "N/A"})
    summary_rows.append({"Metric": "Date Range End", "Value": str(date_range[1]) if date_range[1] else "N/A"})
    summary_rows.append({"Metric": "Total Sites", "Value": len(sites)})
    summary_rows.append({"Metric": "Total Towers", "Value": len(towers)})
    summary_rows.append({"Metric": "Total Carriers", "Value": len(carriers)})
    for src, cnt in source_breakdown:
        summary_rows.append({"Metric": f"Rows ({src})", "Value": cnt})
    df_summary = pd.DataFrame(summary_rows)

    # Sheet 3: Power Model Config
    power_rows = [
        {"Parameter": "Carrier A Watts", "Value": pconfig["carrier_a_watts"], "Unit": "W"},
        {"Parameter": "Carrier B Watts", "Value": pconfig["carrier_b_watts"], "Unit": "W"},
        {"Parameter": "Carrier C Watts", "Value": pconfig["carrier_c_watts"], "Unit": "W"},
        {"Parameter": "Load Scaling Factor", "Value": pconfig["load_scaling_factor"], "Unit": "ratio"},
        {"Parameter": "Max Tower Power", "Value": compute_max_tower_power(pconfig), "Unit": "W"},
        {"Parameter": "Min Tower Power (A only)", "Value": compute_tower_power(True, False, False, 50, 50, 50, pconfig), "Unit": "W"},
    ]
    df_power = pd.DataFrame(power_rows)

    # Sheet 4: Capacity Config
    cap_rows = [
        {"Parameter": "Capacity Ceiling", "Value": pconfig["capacity_ceiling"], "Unit": "%"},
        {"Parameter": "Target Band Low", "Value": pconfig["target_band_low"], "Unit": "%"},
        {"Parameter": "Target Band High", "Value": pconfig["target_band_high"], "Unit": "%"},
    ]
    df_cap = pd.DataFrame(cap_rows)

    # Sheet 5: Decision Statistics
    decisions = db.query(models.Decision).all()
    mode_counts = {}
    total_power_actual = 0
    total_power_baseline = 0
    for d in decisions:
        mode_counts[d.mode] = mode_counts.get(d.mode, 0) + 1
        total_power_actual += d.power_watts
        total_power_baseline += compute_max_tower_power(pconfig)

    stats_rows = [{"Metric": "Total Decisions", "Value": len(decisions)}]
    for mode, count in sorted(mode_counts.items()):
        pct = round(count / len(decisions) * 100, 1) if decisions else 0
        stats_rows.append({"Metric": f"Mode: {mode}", "Value": f"{count} ({pct}%)"})
    if decisions:
        saved_kwh = round((total_power_baseline - total_power_actual) / 1000, 3)
        stats_rows.append({"Metric": "Total Energy Saved", "Value": f"{saved_kwh} kWh"})
        stats_rows.append({"Metric": "Avg Power Actual", "Value": f"{round(total_power_actual / len(decisions), 1)} W"})
        stats_rows.append({"Metric": "Avg Power Baseline", "Value": f"{round(total_power_baseline / len(decisions), 1)} W"})
    df_stats = pd.DataFrame(stats_rows)

    # Sheet 6: Model Accuracy
    model_runs = db.query(models.ModelRun).order_by(models.ModelRun.trained_at).all()
    run_rows = []
    for r in model_runs:
        run_rows.append({
            "Run ID": r.id,
            "Trained At": r.trained_at.isoformat() if r.trained_at else "",
            "Model Type": r.model_type,
            "Training Rows": r.training_row_count,
            "MAE (%)": r.mae,
            "RMSE (%)": r.rmse,
            "Notes": r.notes,
        })
    df_runs = pd.DataFrame(run_rows) if run_rows else pd.DataFrame(columns=["Run ID", "Trained At", "Model Type", "Training Rows", "MAE (%)", "RMSE (%)", "Notes"])

    # Sheet 7: Daily Energy Summary
    from datetime import timedelta
    daily = {}
    for d in decisions:
        day_str = str(d.date)
        if day_str not in daily:
            daily[day_str] = {"actual_wh": 0, "baseline_wh": 0}
        daily[day_str]["actual_wh"] += d.power_watts
        daily[day_str]["baseline_wh"] += compute_max_tower_power(pconfig)

    energy_rows = []
    for day_str in sorted(daily.keys()):
        dd = daily[day_str]
        saved_pct = round((1 - dd["actual_wh"] / dd["baseline_wh"]) * 100, 1) if dd["baseline_wh"] > 0 else 0
        energy_rows.append({
            "Date": day_str,
            "Actual kWh": round(dd["actual_wh"] / 1000, 3),
            "Baseline kWh": round(dd["baseline_wh"] / 1000, 3),
            "Saved kWh": round((dd["baseline_wh"] - dd["actual_wh"]) / 1000, 3),
            "Saved %": saved_pct,
        })
    df_energy = pd.DataFrame(energy_rows)

    # Write all sheets
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df_site.to_excel(writer, index=False, sheet_name="Site Overview")
        df_summary.to_excel(writer, index=False, sheet_name="Data Summary")
        df_power.to_excel(writer, index=False, sheet_name="Power Model")
        df_cap.to_excel(writer, index=False, sheet_name="Capacity Config")
        df_stats.to_excel(writer, index=False, sheet_name="Decision Statistics")
        df_runs.to_excel(writer, index=False, sheet_name="Model Accuracy")
        if not df_energy.empty:
            df_energy.to_excel(writer, index=False, sheet_name="Daily Energy")

    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=thesis_report.xlsx"},
    )


def _build_demo_summary_excel(date_from: date, date_to: date, db: Session) -> BytesIO:
    from datetime import timedelta
    from app.services.power import get_power_config

    pconfig = get_power_config(db)
    p_a = pconfig.get("carrier_a_watts", 300.0)
    p_b = pconfig.get("carrier_b_watts", 200.0)
    p_c = pconfig.get("carrier_c_watts", 100.0)

    towers = db.query(models.Tower).all()
    tower_a = next((t for t in towers if "A" in t.tower_label.upper()), towers[0] if towers else None)
    tower_b = next((t for t in towers if "B" in t.tower_label.upper()), towers[1] if len(towers) > 1 else tower_a)

    carriers = db.query(models.Carrier).all()
    carrier_map = {}
    for c in carriers:
        carrier_map[(c.tower_id, c.sector_label)] = c

    decisions = (
        db.query(models.Decision)
        .filter(models.Decision.date >= date_from, models.Decision.date <= date_to)
        .order_by(models.Decision.date, models.Decision.hour)
        .all()
    )

    dec_by_key = {}
    for d in decisions:
        key = (d.date, d.hour, d.tower_id)
        if key not in dec_by_key:
            dec_by_key[key] = d

    def _get_pred_prb(tower_id, sector_label, dt_date, hour):
        c = carrier_map.get((tower_id, sector_label))
        if c:
            pred = (
                db.query(models.Prediction)
                .filter(models.Prediction.carrier_id == c.id, models.Prediction.target_date == dt_date, models.Prediction.target_hour == hour)
                .first()
            )
            if pred:
                return pred.predicted_prb
        return 50.0

    data_rows = []
    log_rows = []

    t_a_energy_actual = 0.0
    t_a_energy_baseline = 0.0
    t_b_energy_actual = 0.0
    t_b_energy_baseline = 0.0

    a1_active = 0
    a2_active = 0
    a3_active = 0
    b1_active = 0
    b2_active = 0
    b3_active = 0

    total_hours = 0

    curr = date_from
    while curr <= date_to:
        for hour in range(24):
            total_hours += 1

            day_str = str(curr)

            d_a = dec_by_key.get((curr, hour, tower_a.id) if tower_a else None)
            d_b = dec_by_key.get((curr, hour, tower_b.id) if tower_b else None)

            a_b_on = d_a.carrier_b_state == "ON" if d_a else True
            a_c_on = d_a.carrier_c_state == "ON" if d_a else True
            b_b_on = d_b.carrier_b_state == "ON" if d_b else True
            b_c_on = d_b.carrier_c_state == "ON" if d_b else True

            prb_a_1 = round(_get_pred_prb(tower_a.id, "A", curr, hour) if tower_a else 50.0, 1)
            prb_a_2 = round(_get_pred_prb(tower_a.id, "B", curr, hour) if tower_a else 50.0, 1)
            prb_a_3 = round(_get_pred_prb(tower_a.id, "C", curr, hour) if tower_a else 50.0, 1)

            prb_b_1 = round(_get_pred_prb(tower_b.id, "A", curr, hour) if tower_b else 50.0, 1)
            prb_b_2 = round(_get_pred_prb(tower_b.id, "B", curr, hour) if tower_b else 50.0, 1)
            prb_b_3 = round(_get_pred_prb(tower_b.id, "C", curr, hour) if tower_b else 50.0, 1)

            pow_a_act = p_a + (p_b if a_b_on else 0) + (p_c if a_c_on else 0)
            pow_a_base = p_a + p_b + p_c
            t_a_energy_actual += pow_a_act
            t_a_energy_baseline += pow_a_base

            pow_b_act = p_a + (p_b if b_b_on else 0) + (p_c if b_c_on else 0)
            pow_b_base = p_a + p_b + p_c
            t_b_energy_actual += pow_b_act
            t_b_energy_baseline += pow_b_base

            a1_active += 1
            if a_b_on: a2_active += 1
            if a_c_on: a3_active += 1

            b1_active += 1
            if b_b_on: b2_active += 1
            if b_c_on: b3_active += 1

            data_rows.append({
                "Days": day_str, "Hour": hour, "TowerA": "A1", "Prb": prb_a_1, "RRU Power": p_a, "Stutus": "ON",
                "Days.1": day_str, "Hour.1": hour, "TowerA.1": "B1", "Prb.1": prb_b_1, "RRU Power.1": p_a, "Stutus.1": "ON"
            })
            data_rows.append({
                "Days": day_str, "Hour": hour, "TowerA": "A2", "Prb": prb_a_2, "RRU Power": p_b, "Stutus": "ON" if a_b_on else "OFF",
                "Days.1": day_str, "Hour.1": hour, "TowerA.1": "B2", "Prb.1": prb_b_2, "RRU Power.1": p_b, "Stutus.1": "ON" if b_b_on else "OFF"
            })
            data_rows.append({
                "Days": day_str, "Hour": hour, "TowerA": "A3", "Prb": prb_a_3, "RRU Power": p_c, "Stutus": "ON" if a_c_on else "OFF",
                "Days.1": day_str, "Hour.1": hour, "TowerA.1": "B3", "Prb.1": prb_b_3, "RRU Power.1": p_c, "Stutus.1": "ON" if b_c_on else "OFF"
            })

            str_a = "A1 active, A2and A3 active" if (a_b_on and a_c_on) else ("A1 active, A2and A3 inactive" if (not a_b_on and not a_c_on) else "A1 active, A2 active, A3 inactive")
            str_b = "B1 active, B2and B3 active" if (b_b_on and b_c_on) else ("B1 active, B2and B3 inactive" if (not b_b_on and not b_c_on) else "B1 active, B2 active, B3 inactive")
            log_rows.append({
                "Days": day_str, "Hour": hour, "Tower A": str_a, "Tower B": str_b
            })

        curr += timedelta(days=1)

    df_data = pd.DataFrame(data_rows)
    df_log = pd.DataFrame(log_rows)

    t_a_saved = t_a_energy_baseline - t_a_energy_actual
    t_a_pct = (t_a_saved / t_a_energy_baseline * 100.0) if t_a_energy_baseline > 0 else 0.0

    t_b_saved = t_b_energy_baseline - t_b_energy_actual
    t_b_pct = (t_b_saved / t_b_energy_baseline * 100.0) if t_b_energy_baseline > 0 else 0.0

    tot_energy_act = t_a_energy_actual + t_b_energy_actual
    tot_energy_base = t_a_energy_baseline + t_b_energy_baseline
    tot_saved = tot_energy_base - tot_energy_act
    tot_pct = (tot_saved / tot_energy_base * 100.0) if tot_energy_base > 0 else 0.0

    comb_active_hours = a2_active + a3_active + b2_active + b3_active
    total_possible_hours = total_hours * 4
    comb_inactive_hours = total_possible_hours - comb_active_hours

    summary_data = [
        {"Metric A": "Total Energy Consumption (W)", "Value": round(t_a_energy_actual, 2), "Unnamed: 2": None, "Metric B": "Total Energy Consumption (W)", "Value.1": round(t_b_energy_actual, 2)},
        {"Metric A": "Total Energy Saved (W)", "Value": round(t_a_saved, 2), "Unnamed: 2": None, "Metric B": "Total Energy Saved (W)", "Value.1": round(t_b_saved, 2)},
        {"Metric A": "Percentage Saved (%)", "Value": round(t_a_pct, 2), "Unnamed: 2": None, "Metric B": "Percentage Saved (%)", "Value.1": round(t_b_pct, 2)},
        {"Metric A": "A1 Active Hours", "Value": a1_active, "Unnamed: 2": None, "Metric B": "B1 Active Hours", "Value.1": b1_active},
        {"Metric A": "A2 Active Hours", "Value": a2_active, "Unnamed: 2": None, "Metric B": "B2 Active Hours", "Value.1": b2_active},
        {"Metric A": "A3  Active Hours", "Value": a3_active, "Unnamed: 2": None, "Metric B": "B3  Active Hours", "Value.1": b3_active},
        {"Metric A": None, "Value": None, "Unnamed: 2": None, "Metric B": None, "Value.1": None},
        {"Metric A": None, "Value": None, "Unnamed: 2": None, "Metric B": None, "Value.1": None},
        {"Metric A": None, "Value": None, "Unnamed: 2": None, "Metric B": None, "Value.1": None},
        {"Metric A": "Metric(Towe A,Towe B)", "Value": "Value", "Unnamed: 2": None, "Metric B": None, "Value.1": None},
        {"Metric A": "Total Energy Consumption (W)", "Value": round(tot_energy_act, 2), "Unnamed: 2": None, "Metric B": None, "Value.1": None},
        {"Metric A": "Total Energy Saved (W)", "Value": round(tot_saved, 2), "Unnamed: 2": None, "Metric B": None, "Value.1": None},
        {"Metric A": "Percentage Saved (%)", "Value": round(tot_pct, 2), "Unnamed: 2": None, "Metric B": None, "Value.1": None},
        {"Metric A": "Active Hours", "Value": comb_active_hours, "Unnamed: 2": None, "Metric B": None, "Value.1": None},
        {"Metric A": "Inctive Hours", "Value": comb_inactive_hours, "Unnamed: 2": None, "Metric B": None, "Value.1": None},
    ]

    df_summary = pd.DataFrame(summary_data)

    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df_data.to_excel(writer, index=False, sheet_name="DAta")
        df_log.to_excel(writer, index=False, sheet_name="Band Status Log")
        df_summary.to_excel(writer, index=False, sheet_name="Summary")

    buf.seek(0)
    return buf


@router.get("/summary-demo")
def export_summary_demo(
    date_from: date = Query(None),
    date_to: date = Query(None),
    db: Session = Depends(get_db),
):
    """Export dataset summary in exact demo of summary.xlsx format (DAta, Band Status Log, Summary)."""
    from datetime import datetime as dt, timedelta
    if not date_from or not date_to:
        min_max = db.query(func.min(models.KpiHourly.date), func.max(models.KpiHourly.date)).first()
        date_from = date_from or (min_max[0] if min_max[0] else dt.now().date())
        date_to = date_to or (min_max[1] if min_max[1] else dt.now().date())

    buf = _build_demo_summary_excel(date_from, date_to, db)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=demo_summary_export_{date_from}_{date_to}.xlsx"},
    )


@router.get("/predictions-demo")
def export_predictions_demo(
    date_from: date = Query(None),
    days: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db),
):
    """Export future predicted data and decisions in demo of summary.xlsx format."""
    from datetime import datetime as dt, timedelta
    from app.services import decision as decision_svc

    start_date = date_from or (dt.now().date() + timedelta(days=1))
    end_date = start_date + timedelta(days=days - 1)

    existing = (
        db.query(models.Decision)
        .filter(models.Decision.date >= start_date, models.Decision.date <= end_date)
        .count()
    )
    if existing == 0:
        count = decision_svc.make_decisions_for_range(start_date, end_date, db)
        db.commit()

    buf = _build_demo_summary_excel(start_date, end_date, db)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=future_predictions_summary_{start_date}_{end_date}.xlsx"},
    )

