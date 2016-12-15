#!/usr/bin/env python

import optparse
import json
import time
import array
from pprint import pprint
import ROOT as r


def main():

    usage = '%prog [options] input.JSON'
    parser = optparse.OptionParser( usage = usage )
    parser.add_option('-d', '--debug', metavar = 'LEVEL', default = 'INFO',
                       help= 'Set the debug level. Allowed values: ERROR, WARNING, INFO, DEBUG. [default = %default]' )
    ( options, args ) = parser.parse_args()

    if len( args ) != 1:
        print "Please provide exactly one input json file."

    input_file = args[0]
    if options.debug == "INFO":
        print "################################"
        print "Use JSON file: " + input_file
        print "################################"
        print ""

    data_list = []
    counter = 0
    counter_Main_Spindle = 0
    counter_Rotary_Table = 0
    machines = []
    variables = []
    variable_info_map_valueTooSmall = {}
    variable_info_map_valueTooLarge = {}
    variable_info_map_Rotary_Table  = {}
    variable_info_map_Main_Spindle  = {}
    time_stamp_map                  = {}
    histo_map                       = {}
    histo2D_vs_time_map             = {}
    profile_vs_time_map             = {}
    histo_map_valid                 = {}
    histo_map_invalid               = {}




    specialHisto_actualSpindleSpeed =  r.TH1F( "actualSpindleSpeed_negative", "", 100, -18000., 0 )

    start_time = time.clock()

    maxtime = 0.

    time_hist = r.TH1F( "time", "", 50, 23610., 86000.)

    # loop over the input file
    with open(input_file) as infile:
        for line in infile:
            data = json.loads( line )

            #count data-point
            counter += 1

            #veto data-points with DB error
            if float( data[ "Error" ] ) > 0:
                print "Error for variable: "
                print data["ValueName"]
                print data["ErrorDescription"]
                continue

            #fill list of different componentID.
            if data[ "componentID" ] not in machines:
                machines.append( data[ "componentID" ] )

            #translate timestamp into seconds after midnight.
            try:
                time_str =   str( data[ "timeStamp"  ]['$date'] ).split("T")[ 1 ].split("Z")[ 0 ]
                hours    = time_str.split(":")[0]
                minutes  = time_str.split(":")[1]
                seconds  = time_str.split(":")[2]
                secondsAfterMidnight = float( hours) * 3600. + float( minutes ) * 60. + float( seconds )
            except:
                #veto data-points which have invalid timestamp
                print "failed to parse timestamp"
                print data[ "timeStamp" ]
                continue

            #print the first data map as an example.
            if counter == 1:
                print "################################"
                print "Example data format: "
                pprint( data )
                print "################################"
                print ""
                print str( data[ "timeStamp"  ]['$date'] )
                print secondsAfterMidnight

            if secondsAfterMidnight > maxtime:
                maxtime = secondsAfterMidnight

            time_hist.Fill( secondsAfterMidnight )

            # init histograms and info list once per varaible.
            if data["ValueName"] not in variables:
                variable_info_map_valueTooSmall[ data["ValueName"] ] = []
                variable_info_map_valueTooLarge[ data["ValueName"] ] = []
                varaible_info_list = [ [ "maxValue", data[ "maxValue" ] ], [ "minValue", data[ "minValue" ] ], [ "ValueUnit", data[ "ValueUnit" ] ], [ "lowerRed", data[ "lowerRed" ] ], \
                                                           [ "lowerYellow", data[ "lowerYellow" ] ],  [ "upperRed", data[ "upperRed" ] ], [ "upperYellow", data[ "upperYellow" ] ] ]
                if str( data[ "componentID" ] ) == "12400000193.Rotary_Table":
                    variable_info_map_Rotary_Table[ data[ "ValueName" ] ] = varaible_info_list
                if str( data[ "componentID" ] ) == "12400000193.Main_Spindle":
                    variable_info_map_Main_Spindle[ data[ "ValueName" ] ] = varaible_info_list

                variables.append( data["ValueName"] )

                bin_number = 100
                histo_map[ data["ValueName"] ] = r.TH1F( data["ValueName"], "", bin_number, float( data[ "minValue" ] ),\
                                                         float( data[ "maxValue" ] ) + ( ( float( data[ "maxValue" ] ) - float( data[ "minValue" ] ) )/ float( bin_number - 1 ) ) )

                histo2D_vs_time_map[ data["ValueName"] ] = r.TH2F( str( data["ValueName"] ) + "_time", "", bin_number, float( data[ "minValue" ] ),\
                                                         float( data[ "maxValue" ] ) + ( ( float( data[ "maxValue" ] ) - float( data[ "minValue" ] ) )/ float( bin_number - 1 ) ), \
                                                         1000, 23610., 86000. )
                profile_vs_time_map[ data["ValueName"] ] = r.TProfile( data["ValueName"] + "_profile", "",100, 23610., 86000. )



            # check if value is out of scope and log it. Veto them?
            if float( data[ "maxValue" ] ) < float( data[ "value" ] ):
                variable_info_map_valueTooLarge[  data["ValueName"] ].append( float( data[ "value" ] ) )
                #continue
            if float( data[ "minValue" ] ) > float( data[ "value" ] ):
                variable_info_map_valueTooSmall[  data["ValueName"] ].append( float( data[ "value" ] ) )
                #continue

            #count number of data-points associated to either of the components.
            if str( data[ "componentID" ] ) == "12400000193.Rotary_Table":
                counter_Rotary_Table += 1
            if str( data[ "componentID" ] ) == "12400000193.Main_Spindle":
                counter_Main_Spindle += 1

            # it was found that many values of "Actual Spindle Speed" are outside of its scope. Make a histogram of those values.
            if data["ValueName"] == "Actual Spindle Speed" and float( data[ "value" ] ) < 0.:
                specialHisto_actualSpindleSpeed.Fill( float( data[ "value" ] ) )

            #if data["statusTyp"] == "GREEN":
            #    #if ( data[ "upperRed" ] != None and data[ "lowerRed" ] != None ) and ( float( data[ "value" ] ) > float( data[ "upperRed" ] ) or float( data[ "value" ] ) < float( data[ "lowerRed" ] ) ):
            #    #if ( data[ "lowerRed" ] != None ) and ( float( data[ "value" ] ) < float( data[ "lowerRed" ] ) ):
            #    if ( data[ "upperRed" ] != None) and ( float( data[ "value" ] ) > float( data[ "upperRed" ] ) ):
            #        print data["statusTyp"]
            #        pprint( data )
            #    continue

            #fill all histograms
            histo_map[ data["ValueName"] ].Fill( float( data[ "value" ] ) )
            histo2D_vs_time_map[ data["ValueName"] ].Fill( float( data[ "value" ] ), secondsAfterMidnight )
            profile_vs_time_map[ data["ValueName"] ].Fill( secondsAfterMidnight, float( data[ "value" ] ) )


    end_time = time.clock()

    #create 2D histograms to investigate correlations between variables.
    actualFeedRate_vs_actualPositionMCS = r.TH2F( "actualFeedRate_vs_actualPositionMCS", "", 100, -600., 600., 100, 0., 360. )

    #Plot means of variables for specific time ranges against each other.
    for i in range(100):
        if profile_vs_time_map[ "Actual Feed Rate" ].GetBinEntries( i ) > 0 or profile_vs_time_map[ "Actual Position MCS" ].GetBinEntries( i ) > 0:
            afr     = profile_vs_time_map[ "Actual Feed Rate" ].GetBinContent( i )
            apMCS   = profile_vs_time_map[ "Actual Position MCS" ].GetBinContent( i )
            actualFeedRate_vs_actualPositionMCS.Fill( afr, apMCS )


    #Save all histograms.
    saveFile_root = "histo.root"
    file1 = r.TFile( saveFile_root, "RECREATE" )
    for key in histo_map.keys():
        histo_map[ key ].Write( str( key ) )
    specialHisto_actualSpindleSpeed.Write( str( "actualSpindleSpeed_negative" ) )
    for key in histo2D_vs_time_map.keys():
        histo2D_vs_time_map[ key ].Write()
    for key in profile_vs_time_map.keys():
        profile_vs_time_map[ key ].Write()
    time_hist.Write()
    actualFeedRate_vs_actualPositionMCS.Write()
    file1.Close()

    #print some general informaton.
    print "################################"
    print "The processing of " + input_file + " took " + str( end_time - start_time ) + " seconds."
    print "################################"
    print ""
    print "variable_info_map_Rotary_Table"
    pprint( variable_info_map_Rotary_Table )
    print ""
    print "variable_info_map_Main_Spindle"
    pprint( variable_info_map_Main_Spindle )
    print ""
    #print "Test"
    #print variable_info_map_Main_Spindle[ "Growth Sensor Length" ][2][1]
    print ""
    print "There are " + str( len( variables ) ) + " variables available for the analysis"
    print variables
    print ""
    print "The file contains information for these machines: "
    print machines
    print "Data entries for Main_Spindle " + str( counter_Main_Spindle )
    print "Data entries for Rotary_Table " + str( counter_Rotary_Table )
    print ""
    print "maxtime"
    print maxtime
    errFile = open('error.txt', 'w')
    pprint( variable_info_map_valueTooSmall, errFile )
    pprint( variable_info_map_valueTooLarge, errFile )

if __name__ == '__main__':
    main()
