## Stochastic Hurricane Catastrophe Model
<p> End-to-end probabilistic hurricane loss model for a Florida residential portfolio, built from real NOAA historical storm data, a physics-based wind field, and a Monte Carlo year-loss simulation.</p>
<hr/>

<!-- ### Output :-
<h4> Loss Report (PDF) :-</h4>
<img width="1833" height="1067" alt="image" src="PASTE_LOSS_REPORT_SCREENSHOT_URL_HERE" />

<h4> Exceedance Probability Curves :-</h4>
<img width="1900" height="834" alt="image" src="PASTE_EP_CURVE_CHART_URL_HERE" />

<h4> Portfolio Accumulation Map (QGIS) :-</h4>
<img width="1900" height="834" alt="image" src="PASTE_QGIS_MAP_SCREENSHOT_URL_HERE" /> -->

<hr/>

### 🛠️ Tech Stack :-

- Python
- SQL (SQLite)
- NumPy / Pandas
- GeoPandas / Shapely / QGIS
- Matplotlib
- WeasyPrint
- Jinja2

<hr/>

### Core Features :-
- Stochastic hurricane event catalog generated from real NOAA HURDAT2 track data
- Holland parametric wind field for physics-based hazard modeling
- HAZUS-style vulnerability curves converting wind speed to financial loss
- 100,000-year Monte Carlo Year Loss Table (YLT) simulation
- AAL, OEP/AEP exceedance probability curves, and PML via SQL window functions
- Geospatial exposure accumulation mapping in QGIS
- Auto-generated client-style PDF loss report

<hr/>

### Stochastic Event Set Generation :-
- Historical Florida hurricane landfalls parsed from NOAA's HURDAT2 dataset (1851-2025)
- Each historical landfall is perturbed in location, pressure, and forward speed to generate a larger synthetic event catalog
- Synthetic event rates are calibrated so total annual frequency matches the historical average
- Wind speed at each event is recomputed from perturbed pressure to keep events physically consistent

<hr/>

### Hazard → Vulnerability → Financial Pipeline :-
- Wind speed at every portfolio location is computed using the Holland (1980) parametric wind field
- Wind speed is converted to a damage ratio using construction-class-specific vulnerability curves
- Damage ratio is applied to Total Insured Value (TIV) to compute ground-up and net-of-deductible loss
- Per-event losses are aggregated into an Event Loss Table (ELT)

<hr/>

### Loss Simulation & Reporting :-
- ELT is simulated across 100,000 years using a compound Poisson process
- Simulated Average Annual Loss (AAL) is validated against the analytical AAL for convergence
- SQL window functions rank simulated years to compute Occurrence and Aggregate Exceedance Probability (OEP/AEP) curves
- Probable Maximum Loss (PML) is reported at 100/250/500/1,000/10,000-year return periods
- Final results are compiled into a polished PDF report with methodology and limitations sections
