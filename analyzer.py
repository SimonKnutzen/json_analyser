#!/usr/bin/env python

import optparse
import json
import time
import sys
import array
import scipy
import numpy
from pprint import pprint
import ROOT as r


def main():

    usage = '%prog [options] input.JSON'
    parser = optparse.OptionParser( usage = usage )
    parser.add_option('-d', '--debug', metavar = 'LEVEL', default = 'INFO',
                       help= 'Set the debug level. Allowed values: ERROR, WARNING, INFO, DEBUG. [default = %default]' )
    parser.add_option('-n', '--number_to_analyse', metavar = 'number_to_analyse', default = '99999999999',
                   help= ' Stop the analysis after the first n data points. [default = %default]' )
    parser.add_option('-c', '--corr', action='store_true' , metavar = 'corr', default = False,
                   help= ' Do correlation plot (takes ~0.5h) [default = %default]' )
    parser.add_option('-f', '--flag', metavar = 'flag', default = 'ALL',
                   help= 'Only analyse events with flag==status (GREEN,YELLOW,RED,ALL). [default = %default]' )

    ( options, args ) = parser.parse_args()

    if len( args ) != 1:
        print "Please provide exactly one input json file."
        sys.exit()

    input_file = args[0]
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

    sampling_rate_map               = {}

    time_stamp_map                  = {}
    histo_map                       = {}
    histo2D_vs_time_map             = {}
    graph_vs_time_map               = {}
    profile_vs_time_map             = {}
    profile_vs_time_forFFT_map      = {}
    graph_freq_map                  = {}

    variable_value_list_map         = {}
    variable_time_list_map          = {}

    variable_value_time_list_map    = {}
    variable_value_time_list_map_sorted = {}

    specialHisto_actualSpindleSpeed =  r.TH1F( "actualSpindleSpeed_negative", "", 100, -18000., 0 )

    start_time = time.clock()

    maxtime = 0.

    time_hist = r.TH1F( "time", "", 50, 23610., 86000.)

    actualFeedRate_vs_actualPositionMCS_pair = {}
    actualFeedRate_vs_actualPositionMCS_pairs = []

    Drive_Temperature_vs_actualPositionMCS_pair = {}
    Drive_Temperature_vs_actualPositionMCS_pairs = []

    Drive_Temperature_vs_actualFeedRate_pair = {}
    Drive_Temperature_vs_actualFeedRate_pairs = []

    # loop over the input file
    with open(input_file) as infile:
        for line in infile:
            data = json.loads( line )

            if str( options.flag ) == "ALL":
                pass
            else:
                if str( options.flag ) == str( data[ "statusTyp" ] ):
                    pass
                else:
                    continue

            #count data-point
            counter += 1

            if counter > int( options.number_to_analyse ):
                break
            #veto data-points with DB error
            if float( data[ "Error" ] ) > 0:
                if options.debug == "WARNING":
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
                if options.debug == "WARNING":
                    print "failed to parse timestamp"
                    print data[ "timeStamp" ]
                continue

            #print the first data map as an example.
            if counter == 1:
                if options.debug == "INFO" or options.debug == "WARNING":
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

                variable_value_list_map[ data["ValueName"] ] = []
                variable_time_list_map[ data["ValueName"] ] = []
                variable_value_time_list_map[ data["ValueName"] ] = []

                sampling_rate_map[ data["ValueName"] ] = r.TH1F( str( data[ "ValueName" ] ) + "deta_t","", 10000, 0.001, 1. )

                varaible_info_list = [ [ "maxValue", data[ "maxValue" ] ], [ "minValue", data[ "minValue" ] ], [ "ValueUnit", data[ "ValueUnit" ] ], [ "lowerRed", data[ "lowerRed" ] ], \
                                                           [ "lowerYellow", data[ "lowerYellow" ] ],  [ "upperRed", data[ "upperRed" ] ], [ "upperYellow", data[ "upperYellow" ] ] ]
                if str( data[ "componentID" ] ) == "12400000193.Rotary_Table":
                    variable_info_map_Rotary_Table[ data[ "ValueName" ] ] = varaible_info_list
                if str( data[ "componentID" ] ) == "12400000193.Main_Spindle":
                    variable_info_map_Main_Spindle[ data[ "ValueName" ] ] = varaible_info_list

                variables.append( data["ValueName"] )

                bin_number = 100
                histo_map[ data["ValueName"] ] = r.TH1F( data[ "ValueName" ], "", bin_number, float( data[ "minValue" ] ),\
                                                         float( data[ "maxValue" ] ) + ( ( float( data[ "maxValue" ] ) - float( data[ "minValue" ] ) )/ float( bin_number - 1 ) ) )

                histo_map[ data["ValueName"] ].GetXaxis().SetTitle( data[ "ValueName" ] )
                histo_map[ data["ValueName"] ].GetYaxis().SetTitle( "Number" )

                histo2D_vs_time_map[ data["ValueName"] ] = r.TH2F( str( data["ValueName"] ) + "_time", "", bin_number, float( data[ "minValue" ] ),\
                                                         float( data[ "maxValue" ] ) + ( ( float( data[ "maxValue" ] ) - float( data[ "minValue" ] ) )/ float( bin_number - 1 ) ), \
                                                         1000, 23610., 86000. )

                histo2D_vs_time_map[ data["ValueName"] ].GetXaxis().SetTitle( data[ "ValueName" ] )
                histo2D_vs_time_map[ data["ValueName"] ].GetYaxis().SetTitle( "Seconds after Midnight" )

                profile_vs_time_forFFT_map[ data["ValueName"] ] = r.TProfile( data["ValueName"] + "_profile2", "",30000, 23610., 86000. )

                profile_vs_time_map[ data["ValueName"] ] = r.TProfile( data["ValueName"] + "_profile", "",100, 23610., 86000. )
                profile_vs_time_map[ data["ValueName"] ].GetXaxis().SetTitle( "Seconds after Midnight" )
                profile_vs_time_map[ data["ValueName"] ].GetYaxis().SetTitle( "Mean " + data[ "ValueName" ] )


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

            #fill all histograms
            histo_map[ data["ValueName"] ].Fill( float( data[ "value" ] ) )
            histo2D_vs_time_map[ data["ValueName"] ].Fill( float( data[ "value" ] ), secondsAfterMidnight )
            profile_vs_time_map[ data["ValueName"] ].Fill( secondsAfterMidnight, float( data[ "value" ] ) )
            profile_vs_time_forFFT_map[ data["ValueName"] ].Fill( secondsAfterMidnight, float( data[ "value" ] ) )
            #variable_value_list_map[ data["ValueName"] ].append( float( data[ "value" ] ) )
            #variable_time_list_map[ data["ValueName"] ].append( secondsAfterMidnight )
            variable_value_time_list_map[ data["ValueName"] ].append( [ secondsAfterMidnight, float( data[ "value" ] ) ] )

    for k in variable_value_time_list_map.keys():
        variable_value_time_list_map_sorted[ k ] = sorted( variable_value_time_list_map[ k ] , key=lambda doublet: doublet[ 0 ] )
        for doublet in variable_value_time_list_map_sorted[ k ]:
            variable_value_list_map[ k ].append( doublet[ 1 ] )
            variable_time_list_map[ k ].append( doublet[ 0 ] )

    for key in variable_value_list_map.keys():
        try:
            x = array.array( 'd', variable_time_list_map[ key ] )
            y = array.array( 'd', variable_value_list_map[ key ] )
            n = len( variable_time_list_map[ key ] )
            graph = r.TGraph( n, x, y )
            graph.SetTitle( key )
            graph.GetXaxis().SetTitle( "time" )
            graph.GetYaxis().SetTitle( str( key ) )
            graph_vs_time_map[ key ] = graph

            for index in range( 0, len( variable_time_list_map[ key ] ) - 1 ):
                    delta_t = variable_time_list_map[ key ][ index + 1 ] - variable_time_list_map[ key ][ index ]
                    sampling_rate_map[ key ].Fill( delta_t )

        except:
            if options.debug == "WARNING":
                print key
                print "Unexpected error:", sys.exc_info()[0]


    # Perform FFT
    print "FFT"
    for key in profile_vs_time_forFFT_map.keys():
        profile = profile_vs_time_forFFT_map[ key ]
        nbinsp = profile.GetNbinsX()

        mylist_x = []
        mylist_y = []

        for i in range( nbinsp ):
            mylist_y.append( profile.GetBinContent( i ) )
            mylist_x.append( profile.GetXaxis().GetBinLowEdge( i ) )

        my_array_x = array.array( "d", mylist_x )
        my_array_y = array.array( "d", mylist_y )
        nbin = len( mylist_x )

        histo_for_fft = r.TH1F( "", "", nbin - 1 , my_array_x )

        for n, entry in enumerate( mylist_y ):
            histo_for_fft.SetBinContent( n, entry )

        result = r.TH1F()
        result = histo_for_fft.FFT( 0, "MAG" )

        nbinr = result.GetNbinsX()

        result_list_x = []
        result_list_y = []

        # Translate output into Frequency
        for i in range( int( float( nbinr )/2. ) ):
            result_list_x.append( float( result.GetXaxis().GetBinLowEdge( i ) ) * ( float( nbinsp ) / ( 86000. - 23610. ) )  * ( 1./float( nbinr ) ) )
            result_list_y.append( float( result.GetBinContent( i )) )

        result_array_x = array.array( 'd', result_list_x )
        result_array_y = array.array( 'd', result_list_y )

        freqGraph = r.TGraph( int( float( nbinr )/2. ), result_array_x, result_array_y )
        freqGraph.GetXaxis().SetTitle( "f (Hz)" )
        freqGraph.GetYaxis().SetTitle( "mag" )

        graph_freq_map[ key ] = freqGraph

    print "FFT end"

    #create 2D histograms to investigate correlations between mean of variables.
    actualFeedRate_vs_actualPositionMCS_mean = r.TH2F( "actualFeedRate_vs_actualPositionMCS_mean", "", 100, -600., 600., 100, 0., 360. )
    #Plot means of variables for specific time ranges against each other.
    for i in range(100):
        if profile_vs_time_map[ "Actual Feed Rate" ].GetBinEntries( i ) > 0 or profile_vs_time_map[ "Actual Position MCS" ].GetBinEntries( i ) > 0:
            afr     = profile_vs_time_map[ "Actual Feed Rate" ].GetBinContent( i )
            apMCS   = profile_vs_time_map[ "Actual Position MCS" ].GetBinContent( i )
            actualFeedRate_vs_actualPositionMCS_mean.Fill( afr, apMCS )

    #create 2D histograms to investigate correlations between variables.

    #Drive_Temperature_vs_actualPositionMCS = r.TH2F( "Drive_Temperature_vs_actualPositionMCS", "", 100, 18., 40., 100, 0., 360. )
    if options.corr:
        cForce_vs_feed_rate = r.TH2F( "cForce_vs_feed_rate", "", 1000, 0., 300, 1000, -50., 50. )
        for pair in variable_value_time_list_map_sorted[ 'Fixture Clamping Force' ]:
            list_2 = variable_value_time_list_map_sorted[ 'Actual Feed Rate' ]
            value_1 = pair[ 1 ]
            pair_2 = min( list_2, key=lambda x: abs( x[ 0 ] - pair[ 0 ] ) )
            value_2 = pair_2[ 1 ]
            if abs( pair_2[ 0 ] - pair[ 0 ] ) > 1:
                continue
            else:
                cForce_vs_feed_rate.Fill( float( value_1 ),  float( value_2 ) )


    Drive_Temperature_vs_actualFeedRate = r.TH2F( "Drive_Temperature_vs_actualFeedRate", "", 100, 0., 100., 100, -600., 600. )
    for pair in Drive_Temperature_vs_actualFeedRate_pairs:
        Drive_Temperature_vs_actualFeedRate.Fill( float( pair[ 'Drive Temperature' ][ 0 ] ),  float( pair[ 'Actual Feed Rate' ][ 0 ] ) )


    #Save all histograms.
    saveFile_root = "histo.root"
    file1 = r.TFile( saveFile_root, "RECREATE" )
    for key in histo_map.keys():
        histo_map[ key ].Write( str( key ) )
        sampling_rate_map[ key ].Write( str( key ) + "_delta_t" )
    #for key in histo2D_vs_time_map.keys():
        histo2D_vs_time_map[ key ].Write()
    #for key in profile_vs_time_map.keys():
        profile_vs_time_map[ key ].Write()
        graph_freq_map[ key ].Write( ( str(key) + "_freq" ) )
        graph_vs_time_map[ key ].Write( str( key ) )
    specialHisto_actualSpindleSpeed.Write( str( "actualSpindleSpeed_negative" ) )
    if options.corr:
        cForce_vs_feed_rate.Write( "cForce_vs_feed_rate" )

    time_hist.Write()
    actualFeedRate_vs_actualPositionMCS_mean.Write()
    #Drive_Temperature_vs_actualPositionMCS.Write()
    file1.Close()

    end_time = time.clock()
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
    print "There are " + str( len( variables ) ) + " variables available for the analysis"
    print variables
    print ""
    print "The file contains information for these machines: "
    print machines
    print "Data entries for Main_Spindle " + str( counter_Main_Spindle )
    print "Data entries for Rotary_Table " + str( counter_Rotary_Table )
    print ""
    print "################################"
    print "The processing of " + input_file + " took " + str( end_time - start_time ) + " seconds."
    print "################################"
    errFile = open('error.txt', 'w')
    pprint( variable_info_map_valueTooSmall, errFile )
    pprint( variable_info_map_valueTooLarge, errFile )

if __name__ == '__main__':
    main()
