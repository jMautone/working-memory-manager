## Purpose

A child process cannot change its parent shell's directory, yet `wcm resume` promises to land the person where the work is. This capability defines the protocol by which the CLI asks the shell to change directory, and the PowerShell wrapper that honours it.

## ADDED Requirements

### Requirement: Directory-change request protocol
When the environment variable `WCM_CD_FILE` names a file, any command that leaves an initiative active whose `path` is a directory that exists SHALL write that path, as a single UTF-8 line, to the named file. The CLI SHALL write nothing to the file in every other case. When `WCM_CD_FILE` is not set, the CLI SHALL behave identically except for the write. Commands that can request a change are `resume`, `new` and `promote --resume`.

#### Scenario: Resume with an existing path
- **WHEN** `WCM_CD_FILE` names an empty temp file, `INIT-0007` records `path: C:\wt\payment-retries`, that directory exists, and the user runs `wcm resume INIT-0007`
- **THEN** the file contains exactly `C:\wt\payment-retries` followed by a newline

#### Scenario: Resume with a missing path
- **WHEN** `INIT-0007` records a path that does not exist on disk and the user runs `wcm resume INIT-0007`
- **THEN** the file stays empty, the brief still prints the `Path:` line, and a warning says the directory is missing

#### Scenario: Command without a path
- **WHEN** `WCM_CD_FILE` is set and the user runs `wcm pause -n "x"` or `wcm now`
- **THEN** the file stays empty

#### Scenario: Direct invocation without the wrapper
- **WHEN** `WCM_CD_FILE` is not set and the user runs the CLI directly with `wcm resume INIT-0007`
- **THEN** the command succeeds, prints the `Path:` line, and does not attempt to change any directory

### Requirement: PowerShell module performs the change
The repository SHALL ship a PowerShell module `shell/wcm.psm1` exporting a function named `wcm`. The function SHALL forward all arguments to the CLI unchanged; run the CLI with stdin, stdout and stderr attached to the console so interactive prompts work; set `WCM_CD_FILE` to a fresh temporary file for the duration of the call; after the CLI exits, change the shell's location to the path in that file if the file is non-empty and the path exists; delete the temporary file; and leave the CLI's exit code in `$LASTEXITCODE`.

#### Scenario: Resume lands in the path
- **WHEN** the module is imported, `INIT-0007` records an existing path, and the user runs `wcm resume INIT-0007` from `C:\`
- **THEN** the prompt is now at `C:\wt\payment-retries` and `$LASTEXITCODE` is 0

#### Scenario: Prompts still work through the wrapper
- **WHEN** the module is imported and the user runs `wcm pause` with an active initiative
- **THEN** the three prompts appear immediately and accept keyboard input

#### Scenario: Failure leaves the location alone
- **WHEN** the user runs `wcm resume INIT-0099` through the wrapper and the ID does not exist
- **THEN** the location is unchanged, the CLI's error is visible, and `$LASTEXITCODE` is non-zero

#### Scenario: Temporary file cleaned up
- **WHEN** any `wcm` command completes through the wrapper
- **THEN** the temporary file named by `WCM_CD_FILE` no longer exists

### Requirement: Wrapper locates the CLI
The module SHALL invoke the installed `wcm` console script when one is found on `PATH`, and otherwise `py -3.14 -m wcm`. It SHALL NOT invoke a bare `python`, which on the target machine resolves to the Microsoft Store alias rather than the installed interpreter. If neither can be started it SHALL print an actionable error mentioning `pip install` and exit non-zero without changing location.

#### Scenario: CLI not installed
- **WHEN** the module is imported on a machine where the package is not installed
- **THEN** running `wcm now` prints an error that mentions `pip install` and `$LASTEXITCODE` is non-zero

### Requirement: Installation is one profile line
The README SHALL document that adding `Import-Module <repo>\shell\wcm.psm1` to the PowerShell profile makes `wcm` available in every new session, and that without the module every command still works except the automatic directory change.

#### Scenario: Import exposes the function
- **WHEN** the user runs `Import-Module .\shell\wcm.psm1`
- **THEN** `Get-Command wcm` reports a function from module `wcm`
