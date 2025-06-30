# FIXME: This script should exit if any part of it fails;
# right now it just continues to run the next command.

ENV_NAME="env"

git submodule update --init
git submodule update --recursive --remote

# Create the conda environment
conda config --set ssl_verify false
conda env create --prefix ${ENV_NAME} --file environment.yml
conda config --append envs_dirs $PWD

CONDA_BASE=$(conda info --base)
source ${CONDA_BASE}/etc/profile.d/conda.sh

# Install the revisions package
# python3 -m pip install -e code/
eval "conda activate ${ENV_NAME}; cd code; pip install -e .; cd .."

# Install MASSAlign
# python3 -m pip install -e massalign/
eval "conda activate ${ENV_NAME}; cd massalign; pip install -e .; cd .."

# Download spaCy model
eval "conda activate ${ENV_NAME}; python -m spacy download en_core_web_sm"