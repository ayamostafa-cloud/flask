import pandas as pd
from flask import Flask, render_template, request
import plotly.express as px
import plotly
import json

# ----------------------------
# LOAD DATA
# ----------------------------
df = pd.read_csv("data/integrated.csv")

# Fix column names
df["crash_date_crash"] = pd.to_datetime(df["crash_date_crash"], errors="coerce")
df["year"] = df["crash_date_crash"].dt.year
df["crash_time_crash"] = pd.to_datetime(df["crash_time_crash"], format="%H:%M", errors="coerce")
df["crash_hour"] = df["crash_time_crash"].dt.hour
df["crash_day"] = df["crash_date_crash"].dt.day_name()

df["borough"] = df["borough"].astype(str).str.upper().str.strip()
df["vehicle_type_code1"] = df["vehicle_type_code1"].replace("", "UNKNOWN").fillna("UNKNOWN")

# ----------------------------
# FLASK APP
# ----------------------------
app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():

    filtered = df.copy()

    borough = None
    year = None
    search = None

    if request.method == "POST":
        borough = request.form.get("borough")
        year = request.form.get("year")
        search = request.form.get("search")

        # -------------------------
        # APPLY FILTERS
        # -------------------------
        if borough and borough != "All":
            filtered = filtered[filtered["borough"] == borough.upper()]

        if year and year != "All":
            filtered = filtered[filtered["year"] == int(year)]

        if search:
            s = search.lower()

            # detect borough in search
            for b in df["borough"].unique():
                if b.lower() in s:
                    filtered = filtered[filtered["borough"] == b]

            # detect year
            for y in df["year"].dropna().unique():
                if str(int(y)) in s:
                    filtered = filtered[filtered["year"] == y]

    # ----------------------------
    # AVOID EMPTY DATA CRASH
    # ----------------------------
    if filtered.empty:
        empty_fig = px.scatter(title="⚠ No Data Available")
        empty_json = json.dumps(empty_fig, cls=plotly.utils.PlotlyJSONEncoder)
        return render_template("index.html",
                               bar=empty_json, pie=empty_json, map=empty_json,
                               line=empty_json, heat=empty_json, hist=empty_json,
                               scatter=empty_json, sunburst=empty_json,
                               boroughs=sorted(df["borough"].unique()),
                               years=sorted(df["year"].dropna().unique()),
                               selected_borough=borough,
                               selected_year=year)

    # ----------------------------
    # 1. BAR CHART – VEHICLE TYPE
    # ----------------------------
    vc = filtered["vehicle_type_code1"].value_counts().nlargest(10).reset_index()
    vc.columns = ["vehicle_type", "count"]

    bar_fig = px.bar(vc, x="vehicle_type", y="count",
                     title="Top 10 Vehicle Types")

    # ----------------------------
    # 2. PIE CHART – INJURED / KILLED
    # ----------------------------
    pie_fig = px.pie(
        names=["Injured", "Killed"],
        values=[
            filtered["number_of_persons_injured"].sum(),
            filtered["number_of_persons_killed"].sum()
        ],
        title="Injuries vs Fatalities"
    )

    # ----------------------------
    # 3. MAP – FIXED (NO WARNINGS)
    # ----------------------------
    map_data = filtered.dropna(subset=["latitude", "longitude"])

    if not map_data.empty:
        map_fig = px.scatter_map(
            map_data,
            lat="latitude",
            lon="longitude",
            color="borough",
            zoom=10,
            title="Crash Locations"
        )
    else:
        map_fig = px.scatter_map(
            lat=[40.7],
            lon=[-74.0],
            zoom=10,
            title="⚠ No Location Data"
        )

    # ----------------------------
    # 4. LINE – CRASHES PER YEAR
    # ----------------------------
    line_data = filtered.groupby("year").size().reset_index(name="count")
    line_fig = px.line(line_data, x="year", y="count",
                       title="Crashes Over the Years", markers=True)

    # ----------------------------
    # 5. HEATMAP – FIXED (CORRECT)
    # ----------------------------
    heat_data = filtered.groupby(["borough", "year"])["number_of_persons_injured"].sum().reset_index()

    heat_fig = px.imshow(
        heat_data.pivot_table(index="borough", columns="year", values="number_of_persons_injured", fill_value=0),
        labels=dict(x="Year", y="Borough", color="Injuries"),
        title="Injuries by Borough × Year"
    )

    # ----------------------------
    # 6. HISTOGRAM – INJURIES
    # ----------------------------
    hist_fig = px.histogram(filtered, x="number_of_persons_injured",
                            nbins=20, title="Injury Count Distribution")

    # ----------------------------
    # 7. SCATTER – INJURED vs KILLED
    # ----------------------------
    scatter_fig = px.scatter(
        filtered,
        x="number_of_persons_injured",
        y="number_of_persons_killed",
        color="borough",
        title="Scatter: Injuries vs Fatalities"
    )

    # ----------------------------
    # 8. SUNBURST – WORKS!
    # ----------------------------
    sun_data = filtered.groupby(["borough", "vehicle_type_code1"]).agg(
        injuries=("number_of_persons_injured", "sum")
    ).reset_index()

    sunburst_fig = px.sunburst(
        sun_data,
        path=["borough", "vehicle_type_code1"],
        values="injuries",
        title="Sunburst: Borough → Vehicle Type → Injuries"
    )

    # ----------------------------
    # CONVERT ALL FIGURES TO JSON
    # ----------------------------
    bar = json.dumps(bar_fig, cls=plotly.utils.PlotlyJSONEncoder)
    pie = json.dumps(pie_fig, cls=plotly.utils.PlotlyJSONEncoder)
    mapj = json.dumps(map_fig, cls=plotly.utils.PlotlyJSONEncoder)
    line = json.dumps(line_fig, cls=plotly.utils.PlotlyJSONEncoder)
    heat = json.dumps(heat_fig, cls=plotly.utils.PlotlyJSONEncoder)
    hist = json.dumps(hist_fig, cls=plotly.utils.PlotlyJSONEncoder)
    scatter = json.dumps(scatter_fig, cls=plotly.utils.PlotlyJSONEncoder)
    sun = json.dumps(sunburst_fig, cls=plotly.utils.PlotlyJSONEncoder)

    return render_template(
        "index.html",
        bar=bar,
        pie=pie,
        map=mapj,
        line=line,
        heat=heat,
        hist=hist,
        scatter=scatter,
        sunburst=sun,
        boroughs=sorted(df["borough"].unique()),
        years=sorted(df["year"].dropna().unique()),
        selected_borough=borough,
        selected_year=year
    )


if __name__ == "__main__":
    app.run(debug=True)
