# PSL 2026 Winner Prediction Engine

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![PyTorch](https://img.shields.io/badge/PyTorch-Deep%20Learning-ee4c2c.svg)
![Scikit-Learn](https://img.shields.io/badge/Scikit--Learn-Machine%20Learning-F7931E.svg)
![Pandas](https://img.shields.io/badge/Pandas-Data%20Wrangling-150458.svg)

An advanced, end-to-end Machine Learning and Deep Learning pipeline designed to forecast the winner of the Pakistan Super League (PSL) 2026 season. This project bridges the gap between raw ball-by-ball cricket data and financial "Star Power" to generate highly calibrated tournament probabilities.

## 1. Data Provenance & ETL Pipeline
Sports data is inherently noisy. To build a robust dataset, information was aggregated and transformed from three distinct streams:
* **On-Field Statistics:** Ball-by-ball JSON records were ingested from [Cricsheet.org](https://cricsheet.org/), ensuring every legal delivery, run, and wicket was officially verified.
* **Historical Roster Data (2016–2025):** Player draft categories (Platinum, Diamond, Gold, Silver, Emerging, Supplementary) were manually extracted and mapped via LLM-assisted string matching to account for naming inconsistencies.
* **2026 Auction Integration:** Inaugural 2026 auction prices were translated back into historical "Draft Tiers" to maintain mathematical continuity for the expansion teams.

## 2. Advanced Feature Engineering
Tree-based algorithms struggle with absolute stats (e.g., "Team A Win Rate"). This pipeline relies heavily on a **Differential Matrix**:
* **The "Star Power" Engine:** A Weighted Category Score is assigned to the Playing XI based on their professional tier (Platinum = 5 pts, Emerging = 1 pt). The model calculates `strength_diff` before a ball is bowled.
* **Dynamic Rolling Form:** Lifetime win rates are too slow to adapt. Win rates are strictly calculated over a **rolling 10-match window**.
* **Experience Gap (`exp_diff`) & Rookie Penalty:** To solve the "Cold Start" problem for 2026 expansion franchises (Rawalpindiz and Hyderabad Kingsmen), new teams are initialized with a penalized 25% baseline win rate and `0` historical experience, forcing the model to respect the difficulty of inaugural seasons.
* **Toss Context:** Maps whether a team is setting a target or chasing (`t1_bat_first`).

## 3. Model Architecture (Hybrid Ensemble)
This engine utilizes a dual-architecture approach to capture both non-linear patterns and stable linear boundaries:

### A. Deep Learning: PyTorch (Curriculum Learning)
A 3-layer Feedforward Neural Network trained chronologically. Using **Curriculum Learning**, the model trains on Season 1 and is *only* allowed to advance to Season 2 once it hits an 80% accuracy threshold, ensuring it masters historical fundamentals before tackling complex recent data.

### B. Machine Learning: Scikit-Learn Voting Ensemble
A soft-voting classifier combining heavily regularized **Logistic Regression**, **Random Forest**, and **Gradient Boosting**. 
* **Walk-Forward Validation:** Trained chronologically to prevent data leakage.
* **Time-Decay Weights:** Recent matches are mathematically weighted heavier than ancient matches (using `np.linspace`), protecting the algorithm from "Concept Drift" (e.g., the COVID-19 disrupted 2020 season).

##  4. The 2026 Simulation Engine
To predict the 2026 Tournament Winner, the pipeline runs a rigorous simulation:
1. **Combinatorics:** Generates every possible Round-Robin matchup using `itertools`.
2. **Toss Averaging:** Because the coin toss is unknown, the engine passes the data through the models twice—once simulating Team A batting first, and once simulating Team B batting first—averaging the exact mathematical probabilities.
3. **Probability Fusion:** Averages the outputs of the PyTorch and ML Ensemble models, normalizing the aggregate points into a final percentage-based Tournament Win Probability.

## How to Run
1. Clone the repository: `git clone [https://github.com/Faizan-Nexus/PSL-2026-Winner-Prediction-Engine]`
2. Install requirements: `pip install -r requirements.txt`
3. Run the complete pipeline in Jupyter or Kaggle: `psl_prediction_pipeline.ipynb`
