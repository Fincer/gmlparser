#!/usr/bin/env python3

#    Simple JPEG2000 GML data parser
#    Copyright (C) 2019  Pekka Helenius
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.

################################################################

import sys
from warnings import warn as Warn
import os.path
import argparse
import re
import xmltodict
import json
import urllib.request as URL
import math
# TODO import csv

# TODO retrieve place name by using metadata coordinates & ref.system info
#   requires internet connection and connection to a valid server
#
# TODO rename JPEG2000 file based on metadata entries, syntax given by user
#
# TODO fix tfw export for JPEG2000 files

################################################################
#
# INPUT ARGUMENTS

argparser = argparse.ArgumentParser()

argparser.add_argument('-i', '--input', help = 'Input JPEG2000 image file', nargs = '?', dest = 'inputfile')
argparser.add_argument('-f', '--dataformat', help = 'Output format (Default: xml; Available: xml | json | [tfw|worldfile] | info)', nargs = '?', dest = 'outputformat')
argparser.add_argument('-o', '--output', help = 'Output file name', nargs = '?', dest = 'outputfile')
argparser.add_argument('-l', '--formatting', help = 'Data formatting (Default: raw; Available: raw, pretty)', nargs = '?', dest = 'formatting')

args = argparser.parse_args()

# Formatting defaults to pretty format
#
if args.formatting is None:
    args.formatting = 'pretty'

################################################################

if not len(sys.argv) > 1:
    argparser.print_help()
    exit(0)

if not args.inputfile.endswith('.jp2'):
    Warn("Warning: Not a valid JPEG2000 file suffix")

if args.outputformat is None:
    raise ValueError("Error: No output format or file specified")

elif args.outputformat not in ('json', 'xml', 'tfw', 'worldfile', 'info'):
    raise ValueError("Error: Not a valid output format")

################################################################
#
# JPEG2000 CHECK STRINGS

# Look for these jp2 strings in file header
#
jp2_header_str = ['ftypjp2', 'jp2 jpx', 'jp2', 'jp2h', 'jp2 J2P1']

# First string to look for in the selected jp2 file
# Basically, we are looking for the start of footer of the file
# which is indicated by this string
#
# We need to convert the string into bytes with encode method
# for the following while loop.
#
mdata_start_str = [ str.encode('gml.data'), str.encode('gxml'), str.encode('fxml') ]
mdata_end_str = str.encode('uuid')

################################################################
#
# OPEN JPEG2000 file

# Open the image file in read-only binary mode
with open(args.inputfile, 'rb') as f:

################################################################
#
# JPEG2000 header check

    # Check for the first 4 file lines
    header_lines = f.readlines()[0:3]

    # Declare a variable to store header text string
    header_str = ''

    # For each header line 1-4...
    for a in header_lines:

        # Decode binary formatted string (bytes -> string conversion) and ignore any errors we encounter
        header_decode = a.decode('utf-8', errors='ignore')

        # Store decoded string into header_str variable
        header_str += header_decode

    # Check existence of each jp2 specific string we have defined in 'jp2_header_str' list above
    for jp2_str in jp2_header_str:

        # If a jp2 specific string is found, set up a new variable t and break the for loop
        if jp2_str in header_str:
            t = ''
            break

    # Variable t is not defined if any valid jp2 string is not found. Thus, this test gives
    # us and exception (NameError) if no any jp2 string is found.
    try:
        t
    except NameError:
        raise ValueError("Error: Not a valid JPEG2000 file")

################################################################
#
# PARSE METADATA LINES

    # Enumerate all lines, look for metadata start line, using
    # string 'mdata_start_str' as a reference
    # Break the loop when found. If not found, abort.
    #
    # Return to the first line again in order to parse footer lines
    f.seek(0)

    for mstart_num, mstart_line in enumerate(f):
        # TODO better formatting for this if statement:
        if mdata_start_str[0] in mstart_line or mdata_start_str[1] in mstart_line or mdata_start_str[2] in mstart_line:
            break
            # else
                # TODO echo cannot found metadata start. Abort

    # TODO should return value 2
    #print(mstart_num)
    #sys.exit()

    # Enumerate all lines, look for metadata end line, using
    # string 'mdata_end_str' as a reference
    # Break the loop when found. If not found, abort.
    #
    f.seek(0)
    for mend_num, mend_line in enumerate(f):
        if mdata_end_str in mend_line:
            break
        # else
            # TODO echo cannot found metadata end. Abort

    # Reset readlines
    #
    # Convert metadata start line from 'str' type to 'list' with split method
    # and merge it with the rest of the metadata lines, defined by readlines method.
    # Type of this line list is 'list', thus we use + operator to combine these
    # lists.
    #
    f.seek(0)
    metadata_lines = mstart_line.split() + f.readlines()[mstart_num:mend_num]
    #mdata_lines = mstart_line.split() + f.readlines()

    # Create a new metadata_str variable where we will store our extracted footer strings.
    metadata_str = ''
    for byteline in metadata_lines:

        # Try decode each metadata line to UTF-8 format.
        # As these lines are binary code, the conversion will fail for some
        # of them. In a case of failure, we let the for loop pass to the next
        # line
        #
        # Add each decoded line into 'footer_str' variable
        #
        try:
            byteline_decoded = byteline.decode('utf-8', errors='strict')
            metadata_str += byteline_decoded

        except Exception:
            pass

    f.close()
    metadata_xml_all = re.sub(r'(^[^<]*)|([^>]$)', '', metadata_str)

    # Create a list element from extracted metadata strings
    metadata_xml_all_list = metadata_xml_all.split()

    # Find the last element containing <> symbols in metadata_xml_list, 
    # get the string between them and store it to new variable
    for i in reversed(metadata_xml_all_list):
        if re.match('</*.*>', i):
            last_tag = re.sub('</|>', '', i)
            break

    # In the original metadata list, find the first occurence of the 'last_tag'
    for firstxml_index, value in enumerate(metadata_xml_all_list):
        if re.match('<' + last_tag + '>?', value):
            break

    # For joined metadata list, delete all list entries presented before our 'last_tag'
    # Convert list to string format
    metadata_parsed_list = metadata_xml_all_list[firstxml_index:]
    metadata_joined_list = ' '.join(metadata_parsed_list)

################################################################
#

class GMLDataParser(object):

    def __init__(self, datalist):
        self.datalist = datalist

    def xmlraw(self):
        return xmltodict.parse(self.datalist)

    def xmlpretty(self):
        return xmltodict.unparse(xmltodict.parse(self.datalist),
        pretty=True,indent="  ",newl="\n")

    def jsonraw(self):
        return json.dumps(xmltodict.parse(self.datalist),
        separators=(',', ':'))

    def jsonpretty(self):
        return json.dumps(xmltodict.parse(self.datalist),
        indent=2, sort_keys=True)

    # Convert GML metadata to JSON tree object
    def jsontree(self):
        return json.loads(self.jsonpretty())

    # Function to get nested key values from JSON data
    # by arainchi
    # https://stackoverflow.com/a/19871956
    def findkey(self, tree, keyvalue):
        if isinstance(tree, list):
            for i in tree:
                for x in self.findkey(i, keyvalue):
                    yield x
        elif isinstance(tree, dict):
            if keyvalue in tree:
                yield tree[keyvalue]
            for j in tree.values():
                for x in self.findkey(j, keyvalue):
                    yield x

gmlparser = GMLDataParser(metadata_joined_list)
gml_json = gmlparser.jsontree()

def findgmlkey(data, gmlkey, num):
    try:
        return list(gmlparser.findkey(data, gmlkey))[num]
    except:
        # In a case we can't parse GML data for this element, return string 'Unknown'
        return str("Unknown")

################################################################
#
# Extract relevant values for TFW file/Worldfile

class GML_Pos_offsetVectors():

    # Sample metadata structure of JPEG2000 files (may differ!):

    # offsetVector_1 and offsetVector_2:
    #
    # gml:FeatureCollection
    #     gml:featureMember
    #         gml:FeatureCollection
    #             gml:featureMember
    #                 gml:RectifiedGridCoverage
    #                     gml:rectifiedGridDomain
    #                         gml:RectifiedGrid
    #                             gml:offsetVector[0]
    #                                 #text
    #                             gml:offsetVector[1]
    #                                 #text
    #
    # gml_pos:
    #
    # gml:FeatureCollection
    #     gml:featureMember
    #         gml:FeatureCollection
    #             gml:featureMember
    #                 gml:RectifiedGridCoverage
    #                     gml:rectifiedGridDomain
    #                         gml:RectifiedGrid
    #                             gml:origin
    #                                 gml:Point
    #                                     gml:pos

    # Find offsetVector elements in the file metadata
    # These elements include field #text which we are searching for

    gml_offsetVector_1 = findgmlkey(gml_json, '#text', 0)
    gml_offsetVector_2 = findgmlkey(gml_json, '#text', 1)

    # Check whether we have gml:pos or gml:coordinates element in the file metadata
    # gml:coordinates is a deprecated type according to opengis.net
    try:
        gml_pos = findgmlkey(gml_json, 'gml:pos', 0)
    except:
        gml_pos = findgmlkey(gml_json, 'gml:coordinates', 0)

    # Convert gml_pos to list type in a case it is string type
    if type(gml_pos) is str:

        # Split values, use any other symbol as a separator except for dot, minus prefix and numbers.
        gml_pos = re.split('[^\-^\d^\.]+', gml_pos)

        # Get semi-major axis of the Earth from ESPG metadata
        # TODO get this actually from metadata!
        #try:
            # Try to get the value
        # Fallback value
        #except:
        earth_axis_semimajor = 6378137

        # Estimated meters for one degree on Earth surface for used ellipsoid model 
        dec_mult = float((2 * math.pi * earth_axis_semimajor) / 360)

    # Declare a new list 'l'
    l = []
    for d in (gml_offsetVector_1, gml_offsetVector_2):
        if type(d) is str:
            d = re.split('[^\-^\d^\.]+', d)

        # Add extracted value to list 'l'
        l += d

    # Assumed length of list gml_pos is either 4 (gml:pos) or 6 (gml:coordinates).
    # We must treat these list types differently.
    # In a case length is either of those, return error.
    #
    # Map correct gml_pos values into new array 'g'
    #
    g = [0] * 4
    if len(l) == 4:
        g[0] = l[0]
        g[1] = l[1]
        g[2] = l[2]
        g[3] = l[3]

    elif len(l) == 6:
        g[0] = l[3]
        g[1] = l[4] # TODO is this correct index?
        g[2] = l[2] # TODO is this correct index?
        g[3] = l[1]

    else:
        raise ValueError("Error: Incorrect worldfile metadata definition for rotational and pixel size values")

    # World file definition
    # https://en.wikipedia.org/wiki/World_file
    #
    # g[0]          = pixel size of X-axis in map units
    # g[1]          = Y-axis rotation
    # g[2]          = X-axis rotation
    # g[3]          = pixel size of Y-axis in map units
    # gml_pos[0]    = X-coordinate of the center of the upper left pixel
    # gml_pos[1]    = Y-coordinate of the center of the upper left pixel

    # TODO should gml_pos[1] value be decreased by -1?

gml_posinfo = GML_Pos_offsetVectors()

################################################################
#
# ESPG INFORMATION RETRIEVAL

class ESPGRetrieval():

    #def __init__(self):
    #try:
    espg_number = int(findgmlkey(gml_json, '@srsName', 0).split(':')[-1])
    #except:
        #Warn("Warning: Not a valid ESPG number found")
        #return
    espg_file = str(espg_number) + '.xml'

    def ESPG_retrieve():
        if not os.path.isfile('./' + espg_file):

            # ESPG XML data URL
            espg_url = 'http://epsg.io/' + espg_file
            urlreq = URL.Request(
                espg_url,
                data = None,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 #(KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'
                }
            )

            # Try to download the XML file and save it
            with open(espg_file, 'w') as espg_of:
                try:
                    espg_of.write(str(URL.urlopen(urlreq).read().decode('utf-8')))
                except:
                    Warn("Warning: Could not download ESPG metadata")

                espg_of.close()

    @staticmethod
    def ESPG_read():
        with open(espg_file, 'r') as espg_rf:
            espg_metadata_list = espg_rf.read()

            espgparser = GMLDataParser(espg_metadata_list)
            espg_json = espgparser.jsonpretty()

        gml_datum          = findgmlkey(espg_json, 'gml:datumName', 0)
        gml_ellipsoid      = findgmlkey(espg_json, 'gml:ellipsoidName', 0)
        gml_coordsys       = findgmlkey(espg_json, 'gml:srsName', 0)

        gml_axis_1_abbrev  = findgmlkey(espg_json, 'gml:axisAbbrev', 0)
        gml_axis_1_dir     = findgmlkey(espg_json, 'gml:axisDirection', 0).capitalize()

        gml_axis_2_abbrev  = findgmlkey(espg_json, 'gml:axisAbbrev', 1)
        gml_axis_2_dir     = findgmlkey(espg_json, 'gml:axisDirection', 1).capitalize()

        # TODO. Have child element #text which contains the actual value
        gml_semimajor_axis = findgmlkey(espg_json, 'gml:semiMajorAxis', 0)
        gml_inverse_flat   = findgmlkey(espg_json, 'gml:inverseFlattening', 0)

#espg_data = ESPGRetrieval()
#espg_data.ESPG_read()
#sys.exit()

################################################################
#
# PHYSICAL AREA SIZE CALCULATOR

def axisCalculator():

    # Axis-based data
    try:
        x_high = float(findgmlkey(gml_json, 'gml:upperCorner', 0).split()[0])
        x_low  = float(findgmlkey(gml_json, 'gml:lowerCorner', 0).split()[0])
        y_high = float(findgmlkey(gml_json, 'gml:upperCorner', 0).split()[1])
        y_low  = float(findgmlkey(gml_json, 'gml:lowerCorner', 0).split()[1])

    except:

        # Pixel-based data
        try:
            x_high = float(findgmlkey(gml_json, 'gml:high', 0).split()[0])
            x_low  = float(findgmlkey(gml_json, 'gml:low', 0).split()[0])
            y_high = float(findgmlkey(gml_json, 'gml:high', 0).split()[1])
            y_low  = float(findgmlkey(gml_json, 'gml:low', 0).split()[1])

        except:
            x_high = "Unknown"
            x_low  = "Unknown"
            y_high = "Unknown"
            y_low  = "Unknown"

    for t in (x_high, x_low, y_high, y_low):
        if type(t) is not float:
            return list([
            'Unknown',
            'Unknown',
            'Unknown',
            'Unknown',
            'Unknown'
            ])

    def RadtoGrad(num):
        rad_to_deg = 180 * num / math.pi
        deg_to_grad = 10 * rad_to_deg / 9
        return deg_to_grad

###############################
# X and Y lengths
# Area size in km^2

    x_length = x_high - x_low 
    y_length = y_high - y_low
    xy_area  = (x_length * y_length) / 1000000

###############################
# Inverse geodetic calculation

    xy_hypotenuse = math.sqrt(x_length ** 2 + y_length ** 2)
    inverse_geod_angle = RadtoGrad(math.atan2(y_length, x_length))

###############################

    return list([
        format(x_length, '.2f'),
        format(y_length, '.2f'),
        format(xy_area,  '.2f'),
        format(xy_hypotenuse, '.2f'),
        format(inverse_geod_angle, '.2f')
        ])

gml_calc = axisCalculator()

################################################################
#
# TFW FORMAT PARSE

def tfwparse():

    worldfile_values = gml_posinfo.g + gml_posinfo.gml_pos

    worldfile_out = ''
    for value in worldfile_values:
        worldfile_out += format(float(value)) + '\n'

    # Return gml_out, remove last empty line
    return worldfile_out[:-1]

################################################################
#
# INFORMATION PARSE

# Extract all important metadata elements

def infoparse():

    def getkeys():

        # TODO these might or might not be defined in JSON data!
        infolist = [
          ['Image Name',                 args.inputfile.split('.')[0]       ],
          ['Source Name',                findgmlkey(gml_json, '@srsName', 0)          ],
          ['GML File Name',              findgmlkey(gml_json, 'gml:fileName', 0)      ],
          ['File Structure',             findgmlkey(gml_json, 'gml:fileStructure', 0) ],
          ['Rectified Grid Coverage ID', findgmlkey(gml_json, '@dimension', 0)        ],
         #['Axis Names',            ' '.join(findgmlkey('gml:axisName', 0)) ],
          ['Map Scale',                         ],
          ['Upper Corner Coordinates',   findgmlkey(gml_json, 'gml:upperCorner', 0)   ],
          ['Lower Corner Coordinates',   findgmlkey(gml_json, 'gml:lowerCorner', 0)   ],
          ['X-axis Length in Meters',    gml_calc[0]                        ],
          ['Y-axis Length in Meters',    gml_calc[1]                        ],
          ['Area Size in Square Kilometers', gml_calc[2]                    ],
          ['Distance of Corners Points in Meters', gml_calc[3]                     ],
          ['Azimuth Angle of Corner Points in Gradians', gml_calc[4] ],
          ['Grid Envelope High',         findgmlkey(gml_json, 'gml:high', 0)          ],
          ['Grid Envelope Low',          findgmlkey(gml_json, 'gml:low', 0)           ],
          ['X-axis Pixel Size in Map Units', gml_posinfo.g[0]               ],
          ['Y-axis pixel size in Map Units', gml_posinfo.g[3]               ],
          ['X-axis Rotation',           gml_posinfo.g[1]                    ],
          ['Y-axis Rotation',           gml_posinfo.g[2]                    ],
          ['Upper Left Pixel X-coordinate Center in Map Units', gml_posinfo.gml_pos[0]   ],
          ['Upper Left Pixel Y-coordinate Center in Map Units', gml_posinfo.gml_pos[1]   ]
          #['EPSG Projection Code',                     
          #['Projection Name',
          #['Projection Area',
          #['Image Area',
        ]

        #row_format ="{:>15}" * (len(teams_list) + 1)
        #print(row_format.format("", *teams_list))
        #for team, row in zip(teams_list, data):
         #   print row_format.format(team, *row)

        #for i in infolist:
        #    print(i)

        #sys.exit()

        for i in range(len(infolist)):
            for j in range(len(infolist[i])):
                    print(infolist[i][j], end=' ')
            print('')

    getkeys()

    #print(gml_source)

################################
#
# OUTPUT WRITING

try:
    args.outputfile

    with open(args.outputfile, 'w') as o:

        if args.outputformat in 'xml':
            if args.formatting in 'pretty':
                o.write(gmlparser.xmlpretty())
            elif args.formatting in 'raw':
                o.write(gmlparser.jsonraw())
            else:
                raise ValueError("Error: Undefined formatting")

        elif args.outputformat in 'json':
            if args.formatting in 'pretty':
                o.write(gmlparser.jsonpretty())
            elif args.formatting in 'raw':
                o.write(gmlparser.jsonraw())
            else:
                raise ValueError("Error: invalid data formatting")

        elif args.outputformat in 'tfw' or args.outputformat in 'worldfile':
            o.write(tfwparse())

        elif args.outputformat in 'info':
            o.write(infoparse())
        else:
            raise ValueError("Error: invalid data format")

except:

    if args.outputformat in 'xml':
        if args.formatting in 'pretty':
            print(gmlparser.xmlpretty())
        elif args.formatting in 'raw':
            print(gmlparser.xmlraw())
        else:
            raise ValueError("Error: Undefined formatting")

    elif args.outputformat in 'json':
        if args.formatting in 'pretty':
            print(gmlparser.jsonpretty())
        elif args.formatting in 'raw':
            print(gmlparser.jsonraw())
        else:
            raise ValueError("Error: Undefined formatting")

    elif args.outputformat in 'tfw' or args.outputformat in 'worldfile':
        print(tfwparse())

    elif args.outputformat in 'info':
        print(infoparse())
    else:
        raise ValueError("Error: invalid data format")
