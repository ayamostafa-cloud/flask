from flask import Flask, render_template, request, jsonify
import pandas as pd
import plotly.express as px

# ------------------------
# Load and Prepare Data
# ------------------------
df = pd.read_csv('data/integrated.csv')

df['crash_date_crash'] = pd.to_datetime(df['crash_date_crash'], errors='coerce')
df['year'] = df['crash_date_crash'].dt.year

df['borough'] = df['borough'].astype(str).str.strip().str.upper()
df['latitude'] = pd.to_numeric(df['latitude'], errors='coerce')
df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce')

app = Flask(__name__)


# ------------------------
# Routes
# ------------------------
@app.route("/")
def index():
    # options for dropdowns
    boroughs = sorted(df['borough'].dropna().unique())
    years = sorted(df['year'].dropna().unique())
    return render_template("index.html", boroughs=boroughs, years=years)


@app.route("/api/charts", methods=["POST"])
def charts():
    data = request.get_json() or {}
    borough = data.get("borough")
    year = data.get("year")
    search_term = data.get("search")

    dff = df.copy()

    # -------- SEARCH LOGIC (same as before) --------
    if search_term:
        term = search_term.lower()
        # search boroughs in text
        for b in df['borough'].dropna().unique():
            if b.lower() in term:
                dff = dff[dff['borough'].str.lower() == b.lower()]

        # search years in text
        for y in df['year'].dropna().unique():
            if str(int(y)) in term:
                dff = dff[dff['year'] == y]

        # example extra search for "pedestrian"
        if 'pedestrian' in term and 'contributing_factor_vehicle_1' in dff:
            dff = dff[dff['contributing_factor_vehicle_1']
                      .str.contains('pedestrian', case=False, na=False)]

    # -------- DROPDOWN FILTERS --------
    if borough:
        dff = dff[dff['borough'] == borough.upper()]
    if year:
        dff = dff[dff['year'] == year]

    # -------- EMPTY DATA CHECK --------
    if dff.empty:
        empty = px.scatter(title="⚠ No data available for the selected filters.")
        empty_dict = empty.to_dict()
        return jsonify({
            "bar": empty_dict,
            "pie": empty_dict,
            "map": empty_dict,
            "line": empty_dict,
            "heat": empty_dict,
            "hist": empty_dict,
            "scatter": empty_dict,
            "sunburst": empty_dict,
        })

    # -------- 1. BAR CHART --------
    bar = px.bar(
        dff['vehicle_type_code1'].value_counts().nlargest(10),
        title="Top 10 Vehicle Types",
        labels={'index': 'Vehicle Type', 'value': 'Count'}
    )

    # -------- 2. PIE CHART --------
    pie = px.pie(
        names=['Injured', 'Killed'],
        values=[dff['number_of_persons_injured'].sum(),
                dff['number_of_persons_killed'].sum()],
        title="Injuries vs Fatalities"
    )

    # -------- 3. MAP --------
    map_data = dff.dropna(subset=['latitude', 'longitude'])

    if map_data.empty:
        map_fig = px.scatter_mapbox(
            lat=[40.7128],
            lon=[-74.0060],
            zoom=9,
            text=["⚠ No location data for this selection"],
            title="⚠ No location data available for this selection.",
            mapbox_style="open-street-map"
        )
    else:
        map_fig = px.scatter_mapbox(
            map_data,
            lat='latitude',
            lon='longitude',
            color='borough',
            zoom=10,
            mapbox_style="open-street-map",
            title="Crash Locations"
        )

    # -------- 4. LINE CHART --------
    line_data = dff.groupby('year').size().reset_index(name='num')
    line = px.line(
        line_data,
        x='year',
        y='num',
        markers=True,
        title="Crashes Over the Years"
    )

    # -------- 5. HEATMAP --------
    pivot = dff.pivot_table(
        values='number_of_persons_injured',
        index='borough',
        columns='year',
        aggfunc='sum',
        fill_value=0
    )
    heat = px.imshow(
        pivot,
        title="Injuries Heatmap (Borough × Year)",
        labels=dict(x="Year", y="Borough", color="Injuries")
    )

    # -------- 6. HISTOGRAM --------
    hist = px.histogram(
        dff,
        x='number_of_persons_injured',
        nbins=20,
        title="Distribution of Injuries Per Crash"
    )

    # -------- 7. SCATTER --------
    scatter = px.scatter(
        dff,
        x='number_of_persons_injured',
        y='number_of_persons_killed',
        color='borough',
        title="Scatter: Injuries vs Fatalities"
    )

    # -------- 8. SUNBURST --------
    sunburst_df = dff.copy()
    sunburst_df['vehicle_type_code1'] = sunburst_df['vehicle_type_code1'].fillna('UNKNOWN')
    sb_group = sunburst_df.groupby(
        ['borough', 'vehicle_type_code1'],
        as_index=False
    )['number_of_persons_injured'].sum()
    sb_group['number_of_persons_injured'] = sb_group['number_of_persons_injured'].replace(0, 1)

    sunburst = px.sunburst(
        sb_group,
        path=['borough', 'vehicle_type_code1'],
        values='number_of_persons_injured',
        title="Sunburst: Borough → Vehicle Type → Injuries"
    )

    # Convert all figures to dicts for Plotly.js
    return jsonify({
        "bar": bar.to_dict(),
        "pie": pie.to_dict(),
        "map": map_fig.to_dict(),
        "line": line.to_dict(),
        "heat": heat.to_dict(),
        "hist": hist.to_dict(),
        "scatter": scatter.to_dict(),
        "sunburst": sunburst.to_dict(),
    })


if __name__ == "__main__":
    app.run(debug=True)
