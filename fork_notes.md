# Fork Notes

## 2026-03-11 (v1.3.1)

### User guide and version bump
- Created comprehensive USER_GUIDE.md with quick-start workflows, pricing explanation, and troubleshooting
- Bumped version to 1.3.1 across all project files (version.py, README.md, USER_GUIDE.md, badges)

## 2026-03-11

### Pricing model hardening
- Switched pricing approach to list-price data plus runtime multipliers.
- Added separate brand multipliers in app logic:
	- Trane multiplier
	- Tridium multiplier
- Wired multipliers into both calculation paths:
	- Single System calculations
	- Multiple Systems calculations
- Added multiplier input fields and validation in UI (must be numeric and > 0).
- Updated fallback warning text to clarify fallback list prices are used and multipliers still apply.

### Product lifecycle cleanup
- Removed obsolete expansion product XM70 from active app paths:
	- Core expansion lists
	- UI checkboxes and output tables
	- Datasheet links
	- CSV pricing row
	- Fallback default pricing row
- Removed obsolete controller product UC600 from active app paths:
	- System controller lists
	- UI controller dropdowns and output tables
	- Controller image/datasheet entries
	- CSV pricing row
	- Fallback default pricing row

### Documentation and repo hygiene
- Added a Pricing Model section in README describing list price + brand multiplier behavior.
- Expanded README into a fuller project overview with features, setup, workflow, catalog, build, roadmap, and license sections.
- Restyled README into a more polished public-facing landing page with badges, an at-a-glance table, stronger copy, and clearer workflow sections.
- Added `assets/readme-preview.svg` as a repo-hosted visual preview for the README hero section.
- Added `.private/` to `.gitignore` for local/private notes.
- Added targeted `.gitignore` patterns for common locally generated result/template/combinations Excel and CSV files.
- Removed unused `all_combinations.xlsx` from the repository root.

### Current active catalog in prices.csv
- S500
- S800
- XM90
- XM30
- XM32
- PM014
- JACE9000
- JACE9005
- JACE9010
- JACE9025
- JACE9100
- JACE9200
- IO-R-16
- IO-R-34

### Latest pricing alignment updates
- Added missing Tridium JACE controllers to prices.csv.
- Converted Tridium JACE controller prices to list prices by dividing by 0.22.
- Added missing Tridium IO module rows (IO-R-16 and IO-R-34) to prices.csv.
- Converted Tridium IO module prices to list prices by dividing by 0.22.
- Synced all active pricing references to match prices.csv across:
	- gui.py controller initializers
	- core.py DEFAULT_PRICES_TEXT fallback data

### UI polish and code quality cleanup
- Adjusted multiplier panel layout so controls are centered and no longer overlap nearby inputs.
- Resolved remaining Pylance diagnostics in active source files.
- Added type-safe/fallback-safe handling for image resampling and canvas image updates in GUI image rendering path.
- Updated typed constructor defaults for controller objects to remove float-vs-int inference noise.
- Current status: no Pylance errors in gui.py or core.py.

### Notes
- Active pricing is now aligned across prices.csv, core.py fallback defaults, and gui.py controller initializers.
- Legacy references to UC600/XM70 still exist under old versions (archived files), but not in the active app code paths.
