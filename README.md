# VAD Framework

VAD (Vessel Activity Detection) Framework is a project developed to detect and analyze suspicious vessel activities using data fusion techniques and machine learning. In this version it's possible detect 4 types of activities:

- Illegal Fishing
- Suspicious
- Anoumalous
- Normal



## Features

- Detection of suspicious vessel activities
- Analysis of ship trajectories
- Identification of illegal fishing patterns
- Detection of vessel encounters
- Analysis of loitering behaviors
- Detection of activities in restricted areas

## References

This code was based in following works:

- do Nascimento, V.D.; Alves, T.A.O.; de Farias, C.M.; Dutra, D.L.C. A Hybrid Framework for Maritime Surveillance: Detecting Illegal Activities through Vessel Behaviors and Expert Rules Fusion. Sensors 2024, 24, 5623. https://doi.org/10.3390/s24175623



## Project Structure

```
.
├── data/                  # Input data (shapefiles, datasets)
├── docs/                  # Documentation and references
├── src/                   # Source code
│   ├── behaviours/       # Behavior detection modules
│   ├── database/         # Database modules
│   ├── rules/            # Rules and restriction zones
│   ├── tools/            # Auxiliary tools
│   └── ui_expert/        # Expert interface
├── templates/            # HTML templates for visualization
└── requirements.txt      # Project dependencies
```

## Installation

1. Clone the repository:
```bash
git clone git@github.com:vindn/vad_framework.git
cd vad_framework
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

The framework can be executed in different ways:

1. Batch processing:
```bash
python main.py
```

2. Stream processing:
```bash
python main_jdl_stream.py
```

3. Expert interfaces:
   The ui was developled using flask.

   a. Cold Start Interface (Data Initialization):
   ```bash
   python ui_coldstart.py
   ```
   The Cold Start interface is used to initialize the system with initial data. It allows experts to:
   - Load and preprocess vessel trajectory data
   - Define initial behavior patterns
   - Set up initial rules and thresholds
   - Configure the metamodel database

   b. Expert Operator Interface:
   ```bash
   python ui_op1.py
   ```
   The Expert Operator interface (Operator 1) is used to evaluate vessel trajectories. It provides:
   - Visualization of vessel trajectories
   - Behavior classification options

   c. Active Learning Interface:
   ```bash
   python ui_active_learning.py
   ```
   The Active Learning interface is used to train the framework through expert feedback. It provides:
   - Model-suggested trajectories for expert evaluation
   - Interactive interface for experts to assess and classify vessel behaviors
   - Continuous model improvement through active learning
   - Real-time feedback on model performance


## Large Files

Some data files and models are too large to be stored on GitHub. These files are split into smaller parts using the `split_large_files.sh` script.

### Extracting Large Files

1. Download all parts of the compressed files (e.g., `file.zip.001`, `file.zip.002`, etc.)

2. To extract the files:
```bash
# If using split zip files
zip -s 0 file.zip.001 --out unsplit.zip
unzip unsplit.zip

# If using tar.gz parts
cat file.tar.gz.part* > file.tar.gz
tar xzf file.tar.gz
```

3. Place the extracted files in their respective directories:

- `data/sintetic/gdf_sintetic.pkl` and `data/sintetic/list_encounters_3meses.pickle`: These files contain synthetic vessel trajectories created from encounter data and fishing trajectories sourced from Marine Cadastre (https://marinecadastre.gov/) and Global Fishing Watch (GFW). These synthetic datasets are used for training the framework.
- `data/sistram/gdf_*_*.pickle`: These files contain AIS (Automatic Identification System) data from the Brazilian coast, covering the period from January 2019 to December 2020. The data is stored in Python pickle format for efficient processing.
- `metamodel.db`: This is a SQLite database file that stores all preprocessed data. It includes:
  - Preprocessed vessel trajectories
  - Detected behaviors and encounters
  - Analysis results
  - Expert evaluations


## License

This project is under the MIT license. See the LICENSE file for details.
