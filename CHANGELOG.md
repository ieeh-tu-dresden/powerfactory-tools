## 3.0.0 (2024-09-05)

### BREAKING CHANGE

- upgrade to PowerFactory 2024 (#263)

### Feat

- extend interface for current and voltage sources (#259)
- extend interface for shunts (#258)
- extend export and import functions and move them to utils.io (#245)
- export optional element data as meta dict (#251)
- extend element selection by filter 'out_of_service' (contributors: @SebastianDD)
- supporting multiple PowerFactory versions (contributors: @sasanjac, @SebastianDD)
- properly mapping `system_type` for loads (contributors: @SebastianDD)
- add PowerFactory ErrorCode Description (contributors: @SebastianDD)
- extend PFTypes with LV and MV Load Types and consider LoadModel for LoadLV (contributors: @SebastianDD, @sasanjac)

### Fix

- update example grids to PF 2024 (#270)
- ipynb examples (#272)
- unique name for multiple nested substation nodes and correct names for lv-loads in topology case (#242)
- line length (#237)
- create warning message for empty LV loads (contributors: @SebastianDD, @sasanjac)
- use PF error codes for application startup (contributors: @SebastianDD)
- multiline description of loads/lv-loads not correctly exported (contributors: @SebastianDD)
- use I-type load model for LV-Loads as default instead of Z-type (contributors: @SebastianDD)
- creation of grid variants (contributors: @SebastianDD)

## 2.1.0 (2024-02-14)

### Feat

- extend functions for time simulation by provision of optional data (contributors: @SebastianDD)
- rework low voltage load naming to include partial load names instead of an index (contributors: @SebastianDD)
- add comfort functions for scenario and grid variants (contributors: @SebastianDD, @sasanjac)
- extend PF types (contributors: @SebastianDD)

### Fix

- update libraries and exported grid data (contributors: @SebastianDD)
- make json export more efficient (contributors: @SebastianDD)
- lengths of lines always null (contributors: @SebastianDD)
- transformer export (contributors: @SebastianDD)
- disable update_value function (contributors: @SebastianDD)

## 2.0.0 (2023-12-21)

### BREAKING CHANGE

- add RMS and EMT simulation control (contributors: @SebastianDD)

### Feat

- update exporter to psdm 2.1 (@contributors: @SebastianDD)
- support export of multi-grid projects (contributors: @sasanjac, @SebastianDD)
- add support for RelFuse objects
- load components have individually assignable phases
- API for PowerFactory calculations (contributors: @sasanjac)

### Fix

- wrong reactive power for producer when external and internal controller settings are different (contributors: @SebastianDD)
- transformer data export incomplete (contributors: @SebastianDD, @sasanjac)
- check if assignment of power factor is correct (contributors: @SebastianDD, @sasanjac)
- handling of possibly infeasible vectorgroups (contributors: @sasanjac, @SebastianDD)
- use proper load models for LV and MV loads
- precise handling of floats
- export max power as `RatedPower`
- automatically update project dirs after creation or deletion of elements
- export neutral line conductance as 0.0 (contributors: @SebastianDD)
- unit settings dir doesn't exist in default PF project (contributors: @SebastianDD)
- controller example (contributors: @SebastianDD)

## 1.5.1 (2023-05-10)

### Fix

- transformer export (contributors: @SebastianDD)

## 1.5.0 (2023-05-05)

### Feat

- add Harmonic Source Type and controller commands (contributors: @SebastianDD, @sasanjac)
- add neutral conductor information to exporter (contributors: @SebastianDD)
- separate schema from powerfactory-tools (contributors: @sasanjac, @SebastianDD)

### Fix

- unit settings dir doesn't exist in default PF project (contributors: @SebastianDD)
- add missing transformer vector groups (contributors: @SebastianDD)
- adapt load controller to schema fix (contributors: @SebastianDD)
- wrong sign for MV_Load Producer (contributors: @SebastianDD  @sasanjac )
- VectorGroup misspelling (#116)
- VectorGroup misspelling (contributors: @SebastianDD, @sasanjac  )
Fixes #115
- update citation file automatically (contributors: @SebastianDD)

## 1.4.2 (2023-03-24)

### Fix

- add neutral to schema phase information (contributors: @sasanjac)

## 1.4.1 (2023-03-22)

### Fix

- add neutral to phase information (contributors: @sasanjac)
- create proper producer name in steadystate case (contributors: @sasanjac)

## 1.4.0 (2023-03-14)

### Feat

- improve error handling and logging (contributors: @sasanjac)
- add phase connection and system types (contributors: @sasanjac, @SebastianDD)
- export all Q-control types (contributors: @sasanjac, @SebastianDD)
- change data model loads rated power values cos phi to array (contributors: @sasanjac, @SebastianDD)

### Fix

- unit settings dir doesn't exist in default PF project (contributors: @sasanjac)

## 1.3.1 (2023-01-16)

### Fix

- add readme to pypi

## 1.3.0 (2023-01-16)

### Feat

- check Units for Loadflow variables (contributors: @sasanjac, @SebastianDD, @PietzoJo)

### Fix

- prevent double listing of elementStates when creating TopologyCase (contributors: @SebastianDD, @sasanjac)
- wrong double prefix for generators in compound models (contributors: @SebastianDD)

## 1.2.1 (2022-11-24)

### Fix

- missed date in zenodo metadata file when bump version number (contributors: @sasanjac)

## 1.2.0 (2022-11-10)

### Feat

- cross check if number of ssc entries match number of related entries in topology (contributors: @sasanjac)

### Fix

- optional parameters default to *, which raises Exceptions (contributors: @sasanjac, @bademaister)
- optional parameters default to *, which raises Exceptions (contributors: @sasanjac, @bademaister)
- consider number of units when creating steadystate_case for producer (contributors: @sasanjac)
- switch transformer node assignment (#43) (contributors: @SebastianDD)
- make StationCubicle in Coupler optional (contributors: @sasanjac)

## 1.1.1 (2022-11-03)

### Fix

- all setpoints in SI (contributors: @SebastianDD)
- consider number of parallel lines (#33) (@SebastianDD, @sasanjac)

## 1.1.0 (2022-10-12)

### Feat

- add schema version (#29)

### Fix

- zenodo meta data (#28)

## 1.0.1 (2022-10-10)

### Fix

- proper handling of LV and MV loads (contributors: @sasanjac, @SebastianDD)

## 1.0.0 (2022-09-19)

### Feat

- initial release
