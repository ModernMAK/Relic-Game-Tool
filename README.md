# Relic SGA Archive Tool
#### Disclaimer
Not affiliated with Sega, Relic Entertainment, or THQ.
#### Warning
This project runs executables (pre-packaged) to encode/decode audio files.
#### Description
A tool for parsing and extracting assets from Relic Entertainment games; primarily Dawn of War I, DoW II, and DoW III. 

## Installation (Pip)
### Installing from PyPI (Recommended)
```
pip install relic-game-tool
```
### Installing from GitHub
For more information, see [pip VCS support](https://pip.pypa.io/en/stable/topics/vcs-support/#git)
```
pip install git+https://github.com/ModernMAK/Relic-Game-Tool
```

## Usage
Via importing the python package, or running the relic from the command line.<br>
### As a Python Library
*Details pending*

### As a Command Line Tool
After installing the package with pip, the tool can be run by entering ```relic``` into the command prompt. The tool will list arguments and sub commands available.
#### Quick Use
In general, it's best to unpack the SGA files to avoid unpacking the SGA for multiple extraction passes.<br>

To unpack SGA files, we can use the following command:
```
relic sga unpack 'DoW directory' -o 'storage path' -r -b -e
```
First, the path to the DoW game is specified, we only use one path to avoid extracting other game assets to the same output directory.<br>
In the case of DoW, the latest game contains almost all assets of the previous releases. <br>
The flag`-o` specifies the output directory, this is optional, but makes it easier to perform the next step, extracting assets. <br>
The `-r` flag will search all files and folders within the directory. <br>
The `-b` flag will not extract archives which contain certain keywords marking them as lower quality assets, this will prevent lower quality assets from overwriting higher quality ones.<br>
The `-e` flag will force the program to crash on an error; in most cases, the output is bad, and a bug report should be submitted.<br>
---
After unpacking the SGA archives, we can extract assets from Relic Chunky files.
```
relic chunky extract {extractor} 'storage path' -o 'extract path' -r -e
```
Extractor expects the 'type' of chunky to extract, running `relic chunky extract` will list available extractors.
First, the path to the unpacked archive, 'storage path' should be the same path used after the `-o` flag. 
The flags `-o`, `-r`, and `-e` function the same as above. 
<br>
## Format Specifications
I've compiled what I've learned on the [Wiki](https://github.com/ModernMAK/Relic-SGA-Archive-Tool/wiki).
It may be lacking compared to the actual python code; for more information, you may wish to examine the `relic\sga`, `relic\chunky`, and `relic\chunky_formats` sub-packages instead.