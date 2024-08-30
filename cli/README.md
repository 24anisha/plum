# PLUM CLI
The CLI for PLUM should be a great way to think about usage scenarios of PLUM. Below should be updated as the CLI is being implemented.

# Installation
`pip install plum-api`

# Usage
Once `plum-api` has been installed, `plum` can be activated anywhere from a terminal. Note that the correct environment for `plum-api` needs to be active.

## Initialization
- `plum init`: Only needs to run for the first time. Initializes the PLUM workspace.

## data
This is for keeping track of the input data for the PLUM run. The following commands can be used:
- `plum add`
- `plum clone`
    - `plum clone csharp`
- `plum clean`

## Actions
- `plum build`: Builds every single repository in the dataset.
- `plum test`: Runs unit tests in every single repository in the dataset.
- `plum coverage`: Generates coverage reports for every single repository in the dataset.

## Sanity check
- `plum verify`: Checks that every repository is as the configuration file has it to be.
