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
