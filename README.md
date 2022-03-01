# NetCloud-Failover-Reporter

## Summary
Reports all failover events that have occurred on a given instance of 
NetCloud since the start of the month and outputs the records to an 
Excel sheet.

_Note: If you have any questions or comments you can always use GitHub 
discussions, or email me at farinaanthony96@gmail.com._

#### Why
Provides insight to failover events that occur for systems using 
NetCloud to monitor their network system(s).

## Requirements
- Python >= 3.9
- configparser >= 5.2.0
- openpyxl >= 3.0.9
- pandas >= 1.4.1
- pytz >= 2021.3
- requests >= 2.27.1
- time-uuid >= 0.2.0

## Usage
- Define which failovers you'd like to track. If you want to track all 
  failovers, make sure to disable the timeframe feature in the config 
  file. If you'd like to specify the days of the week and timeframes 
  per specified day of the week, enable the timeframe feature.
  
- Edit the config file with relevant NetCloud API information, the
  timeframe feature information, the timezone the devices on NetCloud 
  are in, and the name of the output Excel file.
    
- Simply run the script using Python:
`python NetCloud-Failover-Reporter.py`
    
## Compatibility
Should be able to run on any machine with a Python interpreter. This 
script was only tested on a Windows machine running Python 3.9.

## Disclaimer
The code provided in this project is an open source example and should 
not be treated as an officially supported product. Use at your own 
risk. If you encounter any problems, please log an
[issue](https://github.com/CC-Digital-Innovation/NetCloud-Failover-Reporter/issues).

## Contributing
1. Fork it!
2. Create your feature branch: `git checkout -b my-new-feature`
3. Commit your changes: `git commit -am 'Add some feature'`
4. Push to the branch: `git push origin my-new-feature`
5. Submit a pull request ツ

## History
- version 2.0.0 - 2022/03/01
    - Major refactor to code and config
    - Added timeframe feature
    - Updated README.md and LICENSE


- version 1.1.2 - 2021/06/07
    - Added support for multiple config files
    - No longer required to have the relative path or file extension in the
      "excel-file-name" field for the config file
    - Updated README.md
    

- version 1.1.1 - 2021/05/17
   - Adjusted README.md
   - Adjusted version number
   - Made relative path for config.ini


-  version 1.1.0 - 2021/03/24
   - Fixed bug where no more than 500 failovers can be processed
   - Removed "Alert Type" column 
   - Added "Info" column
   - Reformatted global variables
   - Edited comments
  

-  version 1.0.0 - 2021/03/17
   - Initial release

## Credits
Anthony Farina <<farinaanthony96@gmail.com>>
