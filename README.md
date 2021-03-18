# NetCloud-Failover-Reporter

## Summary
Reports all failover events that have occurred on a given instance of 
NetCloud since the start of the month and outputs the records to an Excel 
sheet.

_Note: If you have any questions or comments you can always use GitHub 
discussions, or email me at farinaanthony96@gmail.com._

#### Why
Provides insight to failover events that occur for systems using NetCloud 
to monitor their network system(s).

## Requirements
- Python >= 3.9.2
- configparser >= 5.0.2
- openpyxl >= 3.0.6
- pandas >= 1.2.2
- pytz >= 2021.1
- requests >= 2.25.1
- time-uuid >= 0.2.0

## Usage
- Clearly define what a "relevant failover" is and use the commented 
  variables and "if" statement to filter out irrelevant failover records.
  
- Edit the config.ini file with relevant NetCloud API information, the 
  timezone the devices on NetCloud are in, the desired column names in the 
  output Excel file, and the name of the output Excel file.
  - _Make sure you request relevant information to place in your Excel 
    columns. Available router information you can extract is here under 
    "routers" -> "routers Endpoint Fields and Filters":
    https://developer.cradlepoint.com/#!/Routers_
    
- Simply run the script using Python:
`python NetCloud-Failover-Reporter.py`
    
## Compatibility
Should be able to run on any machine with a Python interpreter. This script 
was only tested on a Windows machine running Python 3.9.2.

## Disclaimer
The code provided in this project is an open source example and should not 
be treated as an officially supported product. Use at your own risk. If you 
encounter any problems, please log an
[issue](https://github.com/CC-Digital-Innovation/NetCloud-Failover-Reporter/issues).

## Contributing
1. Fork it!
2. Create your feature branch: `git checkout -b my-new-feature`
3. Commit your changes: `git commit -am 'Add some feature'`
4. Push to the branch: `git push origin my-new-feature`
5. Submit a pull request ツ

## History
-  version 1.0.0 (initial release) - 2021/03/17

## Credits
Anthony Farina <<farinaanthony96@gmail.com>>

## License
MIT License

Copyright (c) [2021] [Anthony G. Farina]

Permission is hereby granted, free of charge, to any person obtaining a 
copy of this software and associated documentation files (the "Software"), 
to deal in the Software without restriction, including without limitation 
the rights to use, copy, modify, merge, publish, distribute, sublicense, 
and/or sell copies of the Software, and to permit persons to whom the 
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in 
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR 
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, 
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE 
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER 
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING 
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER 
DEALINGS IN THE SOFTWARE.