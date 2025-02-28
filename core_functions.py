from qgis import processing
from qgis.core import (QgsProperty, 
                        QgsVectorFileWriter, 
                        QgsVectorLayer, 
                        QgsField, 
                        QgsExpressionContext, 
                        QgsExpressionContextUtils, 
                        edit, 
                        QgsExpression, 
                        QgsCoordinateReferenceSystem, 
                        QgsProcessingFeatureSourceDefinition,
                        QgsFeatureRequest, 
                        QgsProject,
                        QgsCoordinateTransformContext,
                        QgsFields,
                        QgsWkbTypes
)
from qgis.utils import iface
from qgis.PyQt.QtCore import QVariant
import pandas as pd
import re
import numpy as np
import os
import fnmatch
import math 
import statistics as stat

def if_not_make(folder_to_make):
    if not os.path.exists(folder_to_make):
        os.makedirs(folder_to_make)

def if_remove(file_path):
    if os.path.exists(file_path):
        os.remove(file_path)

def find(pattern, path):
    result = []
    for root, dirs, files in os.walk(path):
        for name in files:
            if fnmatch.fnmatch(name, pattern):
                result.append(os.path.join(root, name))
    return result

def downloading_ways(extent,extent_quickosm,OSM_ways_gpkg):
    params = {'QUERY':'[out:xml] [timeout:25];\n(    \n    way["highway"="service"]('+str(extent)+');\n    way["highway"="living_street"]('+str(extent)+');\n    way["highway"="motorway"]('+str(extent)+');\n    way["highway"="primary"]('+str(extent)+');\n    way["highway"="secondary"]('+str(extent)+');\n    way["highway"="tertiary"]('+str(extent)+');\n    way["highway"="residential"]('+str(extent)+');\n    way["highway"="unclassified"]('+str(extent)+');\n    way["highway"="motorway_link"]('+str(extent)+');\n    way["highway"="primary_link"]('+str(extent)+');\n    way["highway"="secondary_link"]('+str(extent)+');\n    way["highway"="tertiary_link"]('+str(extent)+');\n    way["highway"="residential"]('+str(extent)+');\n    way["highway"="motorway_junction"]('+str(extent)+');\n    \n  \t\n);\n(._;>;);\nout body;',
                    'TIMEOUT':180,
                    'SERVER':'https://overpass-api.de/api/interpreter',
                    'EXTENT':extent_quickosm,
                    'AREA':'',
                    'FILE': OSM_ways_gpkg}
    processing.run("quickosm:downloadosmdatarawquery", params)
            

def downloading_railway(extent, extent_quickosm,OSM_tramways_gpkg,trnsprt):

    params = {'QUERY':'[out:xml] [timeout:25];\n(    \n    way["railway"="'+str(trnsprt)+'"]('+str(extent)+');\n    \n  \t\n);\n(._;>;);\nout body;',
            'TIMEOUT':180,
            'SERVER':'https://overpass-api.de/api/interpreter',
            'EXTENT':extent_quickosm,
            'AREA':'',
            'FILE': OSM_tramways_gpkg}
    processing.run("quickosm:downloadosmdatarawquery", params)

def highway_average_speed(OSM_roads_csv,highway_speed_csv): 
           
    city_roads = pd.read_csv(OSM_roads_csv,low_memory=False)

    ls_highway = city_roads.highway.unique()

    highway_speed = pd.DataFrame(ls_highway)

    highway_speed = highway_speed.rename(columns={0:'highway'})

    i_hgw = 0
    while i_hgw < len(highway_speed):
        ls_speeds = []
        Roads = city_roads[city_roads['highway'] == highway_speed.loc[i_hgw,'highway']].reset_index(drop=True)
        all_speeds = list(Roads['maxspeed'])
        i_row = 0
        while i_row < len(all_speeds):
            if str(all_speeds[i_row]).isnumeric():
                ls_speeds.append(int(all_speeds[i_row]))
            i_row += 1
        if ls_speeds: 
            highway_speed.loc[i_hgw,'average_speed'] = stat.mean(ls_speeds)
        i_hgw += 1
        del Roads, i_row, ls_speeds, all_speeds

    highway_speed['bus_lanes'] = highway_speed['average_speed']*2

    highway_speed.to_csv(highway_speed_csv,index=False)

def busroutes(bus_lanes_name, OSM_bus_lanes_gpkg,OSM_roads_gpkg,highway_speed_csv):

    # extract bus lanes in a gpkg
    bus_lanes_selection = '"bus" is not NULL OR "bus:lanes" is not NULL OR "bus:lanes:backward" is not NULL OR "bus:lanes:forward" is not NULL OR "busway" is not NULL OR "busway:left" is not NULL OR "busway:left" is not NULL   OR "busway:right" is not NULL OR "busway:right" is not NULL   OR "hgv" is not NULL OR "hgv:lanes" is not NULL OR "lanes:bus" is not NULL OR "lanes:bus:backward" is not NULL OR "lanes:bus:forward" is not NULL OR "lanes:psv" is not NULL   OR "lanes:psv:forward" is not NULL   OR "maxheight:physical" is not NULL   OR "oneway:bus" is not NULL   OR "oneway:psv" is not NULL   OR "trolley_wire" is not NULL   OR "trolleybus" is not NULL   OR "tourist_bus:lanes" is not NULL   OR "psv" is not NULL   OR "psv:lanes" is not NULL   OR "highway" is \'busway\' OR "psv:lanes:forward" is not NULL OR "psv:lanes:backward" is not NULL'
    params = {'INPUT':OSM_roads_gpkg,
            'EXPRESSION':bus_lanes_selection,
            'OUTPUT':OSM_bus_lanes_gpkg}
    processing.run("native:extractbyexpression", params)
    
    bus_lanes_layer = QgsVectorLayer(OSM_bus_lanes_gpkg,bus_lanes_name,"ogr")
    pr = bus_lanes_layer.dataProvider()
    pr.addAttributes([QgsField("oneway_routing", QVariant.String),
                      QgsField("maxspeed_routing",  QVariant.Int)])
    bus_lanes_layer.updateFields()

    expression1 = QgsExpression('IF("bus:lanes:backward" is not NULL OR "busway:left" is not NULL OR "lanes:bus:backward" is not NULL OR "psv:lanes:backward" is not NULL OR "oneway:bus" is \'no\' OR "onewqy:psv" is \'no\', \'backward\',\'forward\')')
    
    highway_speed = pd.read_csv(highway_speed_csv)
    condition = 'if("maxspeed" is not NULL AND regexp_match("maxspeed",\'[0-9]+\'), "maxspeed"*\'2\', '
    brakets = ')'
    i_row = 0

    while i_row < len(highway_speed):
        highway_type = highway_speed.loc[i_row,'highway']
        speed = int(highway_speed.loc[i_row,'bus_lanes'])
        to_add = 'if("highway" is \''+str(highway_type)+'\',\''+str(speed)+'\', '
        condition = str(condition)+str(to_add)
        brakets = str(brakets)+')'
        i_row += 1

    condition = str(condition)+'\'80\' '+str(brakets)
    expression2 = QgsExpression(condition)

    context = QgsExpressionContext()
    context.appendScopes(QgsExpressionContextUtils.globalProjectLayerScopes(bus_lanes_layer))

    with edit(bus_lanes_layer):
        for f in bus_lanes_layer.getFeatures():
            context.setFeature(f)
            f['oneway_routing'] = expression1.evaluate(context)
            bus_lanes_layer.updateFeature(f)
    bus_lanes_layer.commitChanges()

    with edit(bus_lanes_layer):
        for f in bus_lanes_layer.getFeatures():
            context.setFeature(f)
            f['maxspeed_routing'] = expression2.evaluate(context)
            bus_lanes_layer.updateFeature(f)
    bus_lanes_layer.commitChanges()

    return OSM_bus_lanes_gpkg, bus_lanes_name

def full_city_roads(OSM_roads_gpkg,bus_lanes_gpkg, full_roads_gpgk, city_roads_name,highway_speed_csv):
    
    road_layer = QgsVectorLayer(OSM_roads_gpkg,city_roads_name,"ogr")
    
    pr = road_layer.dataProvider()
    pr.addAttributes([QgsField("oneway_routing", QVariant.String),
                      QgsField("maxspeed_routing", QVariant.Int)])
    road_layer.updateFields()

    expression1 = QgsExpression('IF("oneway" is \'yes\' OR "junction" is \'roundabout\' ,\'forward\',NULL)')
        
    highway_speed = pd.read_csv(highway_speed_csv)
    condition = 'if("maxspeed" is not NULL AND regexp_match("maxspeed",\'[0-9]+\'), "maxspeed", '
    brakets = ')'
    i_row = 0

    while i_row < len(highway_speed):
        highway_type = highway_speed.loc[i_row,'highway']
        speed = int(highway_speed.loc[i_row,'average_speed'])
        to_add = 'if("highway" is \''+str(highway_type)+'\',\''+str(speed)+'\', '
        condition = str(condition)+str(to_add)
        brakets = str(brakets)+')'
        i_row += 1

    condition = str(condition)+'\'40\' '+str(brakets)
    expression2 = QgsExpression(condition)

    context = QgsExpressionContext()
    context.appendScopes(QgsExpressionContextUtils.globalProjectLayerScopes(road_layer))

    with edit(road_layer):
        for f in road_layer.getFeatures():
            context.setFeature(f)
            f['oneway_routing'] = expression1.evaluate(context)
            road_layer.updateFeature(f)
    road_layer.commitChanges()
    
    with edit(road_layer):
        for f in road_layer.getFeatures():
            context.setFeature(f)
            f['maxspeed_routing'] = expression2.evaluate(context)
            road_layer.updateFeature(f)
    road_layer.commitChanges()

    ls_roads=[str(OSM_roads_gpkg),str(bus_lanes_gpkg)]

    params = {'LAYERS':ls_roads,
              'CRS':QgsCoordinateReferenceSystem('EPSG:4326'),
              'OUTPUT':full_roads_gpgk}
    processing.run("native:mergevectorlayers",params)

def Ttbls_plus(Ttlbs_txt,Ttbls_plus_csv,dwnldfld,trips_txt):
    Ttbls_orig = pd.read_csv(Ttlbs_txt)

    Ttbls_orig.to_csv(Ttlbs_txt,index_label='orig_id')

    Ttbls = pd.read_csv(Ttlbs_txt)

    Ttbls['prnt_stp_id']= ""

    i_row = 0

    #calculate the parent_stop_id in Ttbls
    while i_row < len(Ttbls):
        Ttbls.loc[i_row,'prnt_stp_id'] = str(Ttbls.loc[i_row,'stop_id'][:7])
        i_row=i_row+1

    i_row = 0

    # merge route_id
    
    trips = pd.read_csv(trips_txt)
    trps = trips[['trip_id','route_id']]
    Ttbls = pd.merge(Ttbls,trps,on='trip_id', how='left')
    
    #join the route_short_name 
    routes = pd.read_csv(str(dwnldfld)+'/routes.txt')
    rts = routes.filter(['route_id','route_short_name','trnsprt','trnsp_shrt_name'],axis=1)

    Ttbls = Ttbls.merge(rts,on='route_id', how='left')
    
    Ttbls.to_csv(Ttbls_plus_csv,index=False)


def Selected_Ttbls(ls_buses,Ttbls_selected_txt,Ttbls_plus_csv):
    
    Ttbls = pd.read_csv(Ttbls_plus_csv)

    Ttbls_selected = Ttbls[Ttbls['trnsp_shrt_name'].isin(ls_buses) ]

    if_remove(Ttbls_selected_txt)
    Ttbls_selected.to_csv(Ttbls_selected_txt, index=False)

def time_tables_perTransport(rt,Ttbls,tempfldr,lstrnsprt):
    
    Ttbl = Ttbls[Ttbls.route_id == rt]
    num = str(Ttbl['route_short_name'].iloc[0])
    trnsprt_type  = str(Ttbl['trnsprt'].iloc[0])
    trnsp_shrt_name  = str(Ttbl['trnsp_shrt_name'].iloc[0])

    if re.findall('[+]',num):
        num = str(re.findall('[a-zA-Z]+|[0-9]+',num)[0])+'plus'
    id_line = 0
    if str(str(trnsprt_type)+str(num)) in lstrnsprt:
        print(str(num)+' already exists, I am creating anotherone')
        id_line = id_line+1
    while str(str(trnsprt_type)+str(num)+'_'+str(id_line)) in lstrnsprt:
        print(str(num)+'_'+str(id_line)+' already exists, I am creating anotherone')
        id_line=id_line+1
    if id_line == 0:
        nametbl = str(trnsprt_type)+str(num)
    else:
        nametbl = str(trnsprt_type)+str(num)+'_'+str(id_line)
    
    Ttbl['line_name'] = nametbl
    Ttbl = Ttbl.reset_index(drop=True)
    pattern = r'[^:]+$'
    i_row = 0
    while i_row < len(Ttbl):
        stop_id = str(Ttbl.loc[i_row, 'stop_id'])
        if re.search('[0-9]+\:',stop_id):
            Ttbl.loc[i_row, 'stp_pltfrm'] = str(re.search(pattern,stop_id).group())
        else:
            Ttbl.loc[i_row, 'stp_pltfrm'] = ''
        i_row += 1
    
    Ttbl_file = str(tempfldr)+'/'+str(nametbl)+'_stop_times.csv'
    Ttbl.to_csv(Ttbl_file, index=False)
    rt_srt_nm = str(Ttbl['route_short_name'].iloc[0])
    return Ttbl, nametbl, Ttbl_file, rt_srt_nm, trnsprt_type, trnsp_shrt_name

    
def preapare_GTFSstops_by_transport(stops_txt, Ttbl_file,trnsprt,tempfolder,shrt_name,tempfolderstptimes):
    stps = pd.read_csv(stops_txt, dtype={'stop_id':str})
    #load the stop times (Time Table) ot the transport
    Ttbl_unsorted = pd.read_csv(Ttbl_file, dtype={'stop_id':str})
    Ttbl = Ttbl_unsorted.sort_values(['trip_id','departure_time','stop_sequence']).reset_index(drop=True)

    #create the stop table per transport
    seq_ls = []

    sequences = pd.DataFrame()

    # create sequence with prnt_stp_id
    i_row = 0
    i_row2 = 1
    seq_init = 0
    seq_end = 0
    i_seq = 0
    i_max = len(Ttbl)-1
    while i_row < i_max:
        if Ttbl.loc[i_row,'stop_sequence'] < Ttbl.loc[i_row2,'stop_sequence']:
            seq_ls.append(str(Ttbl.loc[i_row,'prnt_stp_id']))
            seq_end += 1
        else:
            seq_ls.append(str(Ttbl.loc[i_row,'prnt_stp_id']))
            
            seq_str = " ".join(seq_ls)
            
            # seq_str = str(seq_ls[0])
            # # add the sequence to the Ttbl
            # i_ls = 1
            # while i_ls < len(seq_ls):
            #     seq_str = str(seq_str) +' '+str(seq_ls[i_ls])
            #     i_ls +=1
            sequences.loc[i_seq,0] = i_seq
            sequences.loc[i_seq,'sequence'] = seq_str
            i_seq += 1
            while seq_init <= seq_end:
                Ttbl.loc[seq_init,'sequence'] = seq_str
                seq_init += 1
            del seq_ls, seq_str #, i_ls
            seq_ls = []
            seq_end += 1
        i_row +=1
        i_row2 +=1

    # add the sequence to the record of the last sequence >bug resolved<
    seq_ls.append(str(Ttbl.loc[i_row,'prnt_stp_id']))
    
    seq_str = " ".join(seq_ls)
    
    # seq_str = str(seq_ls[0])
    # i_ls = 1
    # while i_ls < len(seq_ls):
    #     seq_str = str(seq_str) +' '+str(seq_ls[i_ls])
    #     i_ls +=1

    sequences.loc[i_seq,0] = i_seq
    sequences.loc[i_seq,'sequence'] = seq_str
    del i_seq
    while seq_init <= seq_end:
        Ttbl.loc[seq_init,'sequence'] = seq_str
        seq_init += 1
    del seq_ls, seq_str # i_ls

    # create listo of unique sequences
    del i_row, i_row2, i_max
    sequences = sequences.rename(columns={0:'id'})
    lsuniseqs = sequences.sequence.unique()

    # create the mother_sequences list without sub-sequences
    lstodelete = []
    mother_sequences = lsuniseqs
    i_row = 0
    i_max = len(lsuniseqs)-1
    while i_row < i_max:
        i_row2 = i_row+1
        while i_row2 < len(lsuniseqs):
            if len(lsuniseqs[i_row]) > len(lsuniseqs[i_row2]):
                seq1 = (lsuniseqs[i_row])
                seq2 = (lsuniseqs[i_row2])
                i_del = i_row2
            else:
                seq2 = (lsuniseqs[i_row])
                seq1 = (lsuniseqs[i_row2])
                i_del = i_row
            if seq2 in seq1:
                if not lsuniseqs[i_del] in lstodelete:
                    lstodelete.append(lsuniseqs[i_del])
            i_row2 +=1
        del i_row2
        i_row +=1
    mother_sequences = [seq for seq in mother_sequences if seq not in lstodelete ]



    # for each Ttbl value add the sequence stop ID
    # to define the position of the stop in the beloging sequence
    i_row = 0
    while i_row < len(mother_sequences):
        moth_seq = mother_sequences[i_row].split(" ")
        ls_repet = []
        for elem in moth_seq:
            if moth_seq.count(elem) > 1:
                ls_repet.append(elem)
        i_row2 = 0
        while i_row2 < len(Ttbl):
            if Ttbl.loc[i_row2,'sequence'] in mother_sequences[i_row]:
                pos = mother_sequences[i_row].split(" ").index(str(Ttbl.loc[i_row2,'prnt_stp_id']))
                row_init = i_row2
                row_after = i_row2+1
                if ls_repet and str(Ttbl.loc[i_row2,'prnt_stp_id']) in ls_repet:
                    sequ_ls = [str(Ttbl.loc[row_init,'prnt_stp_id'])]
                    while row_after < len(Ttbl) and Ttbl.loc[row_init,'stop_sequence'] < Ttbl.loc[row_after,'stop_sequence'] :
                        sequ_ls.append(str(Ttbl.loc[row_after,'prnt_stp_id']))
                        row_init +=1
                        row_after +=1 
                    sequ_str = " ".join(sequ_ls)
                    idx_ls = 0
                    while idx_ls < len(moth_seq):
                        if not sequ_str in " ".join(moth_seq[idx_ls:len(moth_seq)]):
                            pos = idx_ls - 1
                            break
                        idx_ls +=1
                        pos = idx_ls-1
                Ttbl.loc[i_row2,'seq_stpID'] = str(trnsprt)+'_trip'+str(i_row+1)+'_pos'+str(pos)
            i_row2 += 1
        i_row += 1



    i_row = 0
    while i_row < len(Ttbl):
        Ttbl.loc[i_row,'trip'] = int(Ttbl.loc[i_row,'seq_stpID'].split('_')[1][4:])
        Ttbl.loc[i_row,'pos'] = int(Ttbl.loc[i_row,'seq_stpID'].split('_')[2][3:])
        i_row += 1
    Ttbl = Ttbl.astype({'trip':'int','pos':'int'})

    Ttbl_with_sequences_csv = str(tempfolderstptimes)+'/'+str(trnsprt)+'_stops_times_with_seq.csv'
    Ttbl.to_csv(Ttbl_with_sequences_csv, index=False)

    # most frequent stops
    ls_GTFS_stops = list(Ttbl.seq_stpID.unique())
    most_freq_stps = pd.DataFrame(ls_GTFS_stops)
    most_freq_stps = most_freq_stps.rename(columns={0:'seq_stpID'})
    i_ls=0
    while i_ls<len(ls_GTFS_stops):  
        ls_stp_id_most_frequent = list(Ttbl['stop_id'][Ttbl['seq_stpID']==ls_GTFS_stops[i_ls]][Ttbl['stp_pltfrm']!=''])
        if ls_stp_id_most_frequent:
            most_freq_stps.loc[i_ls,'stop_id'] = max(set(ls_stp_id_most_frequent), key=ls_stp_id_most_frequent.count)
        else:
            most_freq_stps.loc[i_ls,'stop_id'] = Ttbl['stop_id'][Ttbl['seq_stpID']==ls_GTFS_stops[i_ls]].iloc[0]
        i_ls += 1
        del ls_stp_id_most_frequent


    i_row = 0
    while i_row < len(most_freq_stps):
        most_freq_stps.loc[i_row,'trip'] = int(most_freq_stps.loc[i_row,'seq_stpID'].split('_')[1][4:])
        most_freq_stps.loc[i_row,'pos'] = int(most_freq_stps.loc[i_row,'seq_stpID'].split('_')[2][3:])
        i_row += 1

    most_freq_stps_unsorted = most_freq_stps.astype({'trip':'int','pos':'int'})
    del most_freq_stps

    most_freq_stps = most_freq_stps_unsorted.sort_values(['trip','pos']).reset_index(drop=True)

    # creation and adding segments
    i_row = 0
    i_row2 = 1
    i_max = len(most_freq_stps) -1 
    while i_row < i_max:
        if most_freq_stps.loc[i_row,'pos'] < most_freq_stps.loc[i_row2,'pos']:
            most_freq_stps.loc[i_row, 'mini_trip'] = str(most_freq_stps.loc[i_row, 'stop_id'])+' '+str((most_freq_stps.loc[i_row2, 'stop_id']))
            most_freq_stps.loc[i_row, 'mini_tr_pos'] = str(trnsprt)+'_trip'+str(most_freq_stps.loc[i_row, 'trip'])+'_pos'+str((most_freq_stps.loc[i_row, 'pos']))+'-pos'+str((most_freq_stps.loc[i_row2, 'pos']))
        i_row += 1
        i_row2 += 1

    if not most_freq_stps.stop_id.dtypes == 'object':
        most_freq_stps = most_freq_stps.astype({'stop_id':'int'})
        most_freq_stps = most_freq_stps.astype({'stop_id':'str'})    
    most_freq_stps = most_freq_stps.merge (stps, how='left', on='stop_id') 

    i=0

    # calculate the parent_stop_id in transport stops table
    while i < len(most_freq_stps):
        most_freq_stps.loc[i,'prnt_stp_id'] = str(most_freq_stps.loc[i,'stop_id'][:7])
        i=i+1
    del i

    
    # calculate the stp_pltfrm in Ttbls
    
    pattern = r'[^:]+$'
    i_row = 0
    while i_row < len(most_freq_stps):
        stop_id = str(most_freq_stps.loc[i_row, 'stop_id'])
        if re.search('[0-9]+\:',stop_id):
            most_freq_stps.loc[i_row, 'stp_pltfrm'] = str(re.search(pattern,stop_id).group())
        else:
            most_freq_stps.loc[i_row, 'stp_pltfrm'] = ''
        i_row += 1
    

    most_freq_stps['line_name'] = trnsprt
    
    most_freq_stps['route_short_name'] = shrt_name
    
    GTFSstops_path = str(tempfolder)+'/'+str(trnsprt)+'_stops_segments.csv'
    if_remove(GTFSstops_path)
    most_freq_stps.to_csv(GTFSstops_path, index =False)
    return GTFSstops_path, Ttbl_with_sequences_csv

def shape_assignement(GTFSstops_csv,Ttbl_file,line_trip_csv,trips_txt):
        
    GTFSstops = pd.read_csv(GTFSstops_csv,dtype={'pos':'int','trip':'int','prnt_stp_id':'str','stop_id':'str'})
    Ttbl = pd.read_csv(Ttbl_file,dtype={'pos':'int','trip':'int','prnt_stp_id':'str','stop_id':'str'})

    i_row = 0
    while i_row < len(GTFSstops):
        GTFSstops.loc[i_row,'line_trip'] = str(GTFSstops.loc[i_row,'line_name'])+'_trip'+str(GTFSstops.loc[i_row,'trip'])
        i_row +=1


    line_trip_df = pd.DataFrame(GTFSstops.line_trip.unique()).rename(columns={0:'line_trip'})
    str_prnt_stp = ''
    i_row = 0
    while i_row < len(line_trip_df):
        GTFSstops_line_trip = GTFSstops[GTFSstops['line_trip'] == line_trip_df.loc[i_row,'line_trip'] ].reset_index(drop=True)
        str_prnt_stp = ''
        i_row2 = 0
        while i_row2 < len(GTFSstops_line_trip):
            str_prnt_stp = str(str_prnt_stp)+' '+str(GTFSstops_line_trip.loc[i_row2,'prnt_stp_id'])
            i_row2 += 1
        
        line_trip_df.loc[i_row,'main_seq'] = str_prnt_stp
        i_row += 1

    trip_id_df = pd.DataFrame(Ttbl.trip_id.unique()).rename(columns={0:'trip_id'})
    str_prnt_stp = ''
    i_row = 0
    while i_row < len(trip_id_df):
        Ttbl_trip = Ttbl[Ttbl['trip_id'] == trip_id_df.loc[i_row,'trip_id'] ].reset_index(drop=True)
        str_prnt_stp = ''
        i_row2 = 0
        while i_row2 < len(Ttbl_trip):
            str_prnt_stp = str(str_prnt_stp)+' '+str(Ttbl_trip.loc[i_row2,'prnt_stp_id'])
            i_row2 += 1
        
        trip_id_df.loc[i_row,'seq'] = str_prnt_stp
        i_row += 1

    i_row = 0
    while i_row < len(trip_id_df):
        line_trip = ''
        i_row2 = 0
        while line_trip == '':
            if str(trip_id_df.loc[i_row,'seq']) in str(line_trip_df.loc[i_row2,'main_seq']):
                line_trip = str(line_trip_df.loc[i_row2,'line_trip'])
            i_row2 += 1
            
        trip_id_df.loc[i_row,'line_trip'] = line_trip
        i_row += 1

    trips = pd.read_csv(trips_txt,index_col='trip_id',dtype='str')

    i_row = 0
    while i_row < len(trip_id_df):
        trip_idx = str(trip_id_df.loc[i_row,'trip_id'])
        trips.loc[trip_idx,'shape_id'] = trip_id_df.loc[i_row,'line_trip']
        i_row += 1

    os.remove(trips_txt)
    trips.to_csv(trips_txt)

    line_trip_df.to_csv(line_trip_csv,index=False)

def angles_tram(city_rails_layer,trnsprt,trnsprt_GTFSstops_file,temp_road_folder,GTFSnm_folder):
    GTFSstopspath = r"file:///{}?crs={}&delimiter={}&xField={}&yField={}".format(trnsprt_GTFSstops_file,"epsg:4326", ",", "stop_lon", "stop_lat")
    GTFSstopslayer = QgsVectorLayer(GTFSstopspath,str(trnsprt)+"_GTFSstops","delimitedtext")
    params = {'INPUT':GTFSstopslayer,
              'DISTANCE':0.00150,
              'SEGMENTS':5,'END_CAP_STYLE':0,'JOIN_STYLE':0,
              'MITER_LIMIT':2,'DISSOLVE':True,'SEPARATE_DISJOINT':False,
              'OUTPUT':str(temp_road_folder)+'/bf_'+str(trnsprt)+'_GTFSstops.gpkg'}
    processing.run("native:buffer", params)
    del params

    #clippint roads to make it smaller
    params = {'INPUT':city_rails_layer,
              'OVERLAY':str(temp_road_folder)+'/bf_'+str(trnsprt)+'_GTFSstops.gpkg',
              'OUTPUT':str(temp_road_folder)+'/cl_'+str(trnsprt)+'_rail.gpkg'}        
    processing.run("native:clip", params)
    del params
    
    spl_file = str(temp_road_folder)+'/Spl_'+str(trnsprt)+'_rail.gpkg'
        
    #splitting in to more simple lines 
    params = {'INPUT':str(temp_road_folder)+'/cl_'+str(trnsprt)+'_rail.gpkg',
              'OUTPUT':spl_file}
    processing.run("native:multiparttosingleparts", params)
    del params

    #splitting in smaller peaces
    #params = {'INPUT':str(temp_road_folder)+'/multiL_'+str(trnsprt)+'_swissroad.gpkg',
    #          'LENGTH':0.00007,
    #          'OUTPUT':spl_file}
    #processing.run("native:splitlinesbylength", params)

    #expression to calculate angle_at_vertex($geometry,0)    
    splt_roads = QgsVectorLayer(spl_file,"Spl_"+str(trnsprt)+"_rail","ogr")
    pr = splt_roads.dataProvider()
    pr.addAttributes([QgsField('stp_angl',QVariant.Double)])
    splt_roads.updateFields
    
    expression = QgsExpression('angle_at_vertex($geometry,0)')

    context = QgsExpressionContext()
    context.appendScopes(QgsExpressionContextUtils.globalProjectLayerScopes(splt_roads))


    with edit(splt_roads):
        for f in splt_roads.getFeatures():
            context.setFeature(f)
            f['stp_angl'] = expression.evaluate(context)
            splt_roads.updateFeature(f)
    
    anglefile = str(temp_road_folder)+'/GTFS'+str(trnsprt)+'_angle.gpkg'
    GTFSnomatchangl = str(GTFSnm_folder)+'/GTFS_NOmatch_RD'+str(trnsprt)+'.gpkg'
    GTFS_NMangcsv = str(GTFSnm_folder)+'/GTFS_NOmatch_RD'+str(trnsprt)+'.csv'

    # join attributes by nearest for angle
    params = {'INPUT':GTFSstopslayer,
            'INPUT_2':splt_roads,
            'FIELDS_TO_COPY':['full_id','osm_id','osm_type','name','highway','stp_angl'],
            'DISCARD_NONMATCHING':True,
            'PREFIX':'nrstrd_',
            'NEIGHBORS':1,
            'MAX_DISTANCE':0.00015,
            'OUTPUT':anglefile,
            'NON_MATCHING':GTFSnomatchangl}
    processing.run("native:joinbynearest", params)
    GTFSnomatchplt = QgsVectorLayer(GTFSnomatchangl,"GTFSnmRD"+str(trnsprt),"ogr")
    QgsVectorFileWriter.writeAsVectorFormat(GTFSnomatchplt,GTFS_NMangcsv,"utf-8",driverName = "CSV")
    del params, context, expression
    return anglefile, GTFSnomatchangl, GTFS_NMangcsv, spl_file

def angles_buses(roadlayer,trnsprt,trnsprt_GTFSstops_file,temp_road_folder,GTFSnm_folder):
    GTFSstopspath = r"file:///{}?crs={}&delimiter={}&xField={}&yField={}".format(trnsprt_GTFSstops_file,"epsg:4326", ",", "stop_lon", "stop_lat")
    GTFSstopslayer = QgsVectorLayer(GTFSstopspath,str(trnsprt)+"_GTFSstops","delimitedtext")
    params = {'INPUT':GTFSstopslayer,
              'DISTANCE':0.00015,
              'SEGMENTS':5,'END_CAP_STYLE':0,'JOIN_STYLE':0,
              'MITER_LIMIT':2,'DISSOLVE':True,'SEPARATE_DISJOINT':False,
              'OUTPUT':str(temp_road_folder)+'/bf_'+str(trnsprt)+'_GTFSstops.gpkg'}
    processing.run("native:buffer", params)
    del params

    #clippint roads to make it smaller
    params = {'INPUT':roadlayer,
              'OVERLAY':str(temp_road_folder)+'/bf_'+str(trnsprt)+'_GTFSstops.gpkg',
              'OUTPUT':str(temp_road_folder)+'/cl_'+str(trnsprt)+'_swissroad.gpkg'}        
    processing.run("native:clip", params)
    del params
    
    spl_file = str(temp_road_folder)+'/Spl_'+str(trnsprt)+'_swissroad.gpkg'
        
    #splitting in to more simple lines 
    params = {'INPUT':str(temp_road_folder)+'/cl_'+str(trnsprt)+'_swissroad.gpkg',
              'OUTPUT':spl_file}
    processing.run("native:multiparttosingleparts", params)
    del params

    #splitting in smaller peaces
    #params = {'INPUT':str(temp_road_folder)+'/multiL_'+str(trnsprt)+'_swissroad.gpkg',
    #          'LENGTH':0.00007,
    #          'OUTPUT':spl_file}
    #processing.run("native:splitlinesbylength", params)

    #expression to calculate angle_at_vertex($geometry,0)    
    splt_roads = QgsVectorLayer(spl_file,"Spl_"+str(trnsprt)+"_roads","ogr")
    pr = splt_roads.dataProvider()
    pr.addAttributes([QgsField('stp_angl',QVariant.Double)])
    splt_roads.updateFields
    
    expression = QgsExpression('angle_at_vertex($geometry,0)')

    context = QgsExpressionContext()
    context.appendScopes(QgsExpressionContextUtils.globalProjectLayerScopes(splt_roads))


    with edit(splt_roads):
        for f in splt_roads.getFeatures():
            context.setFeature(f)
            f['stp_angl'] = expression.evaluate(context)
            splt_roads.updateFeature(f)
    
    anglefile = str(temp_road_folder)+'/GTFS'+str(trnsprt)+'_angle.gpkg'
    GTFSnomatchangl = str(GTFSnm_folder)+'/GTFS_NOmatch_RD'+str(trnsprt)+'.gpkg'
    GTFS_NMangcsv = str(GTFSnm_folder)+'/GTFS_NOmatch_RD'+str(trnsprt)+'.csv'

    # join attributes by nearest for angle
    params = {'INPUT':GTFSstopslayer,
            'INPUT_2':splt_roads,
            'FIELDS_TO_COPY':['full_id','osm_id','osm_type','name','highway','stp_angl'],
            'DISCARD_NONMATCHING':True,
            'PREFIX':'nrstrd_',
            'NEIGHBORS':1,
            'MAX_DISTANCE':0.00015,
            'OUTPUT':anglefile,
            'NON_MATCHING':GTFSnomatchangl}
    processing.run("native:joinbynearest", params)
    GTFSnomatchplt = QgsVectorLayer(GTFSnomatchangl,"GTFSnmRD"+str(trnsprt),"ogr")
    QgsVectorFileWriter.writeAsVectorFormat(GTFSnomatchplt,GTFS_NMangcsv,"utf-8",driverName = "CSV")
    del params, context, expression
    return anglefile, GTFSnomatchangl, GTFS_NMangcsv, spl_file

def angle_onRD_sidewalk(GTFSstops_angle, GTFSstops_angle_sidewalk_gpkg,GTFSstops_angle_OSMonROADline_gpkg, agency_txt):
    agency = pd.read_csv(agency_txt)
    ls_agency = agency.agency_id.unique()
    if 881 in ls_agency:
        dist = 0.00001
    else:
        dist = 0.001
    params = {'INPUT': GTFSstops_angle,
                'EXPRESSION':'"distance" > '+str(dist),
                'OUTPUT': GTFSstops_angle_sidewalk_gpkg,
                'FAIL_OUTPUT': GTFSstops_angle_OSMonROADline_gpkg}
    processing.run("native:extractbyexpression", params)

def rectangles_sidewalk(GTFSstops_angle_sidewalk_gpkg, buses_long,tram_long, line_name, GTFSstps_rect_sidewalk_gpkg, GTFSstps_rect_sidewalk_csv,trnsprt_type):

    rect_type = 'sidewalk'
    
    if trnsprt_type == 'Tram' or trnsprt_type == 'RegRailServ' or trnsprt_type == 'Funicular' :
        trnsprt_long = tram_long
    else:
        trnsprt_long = buses_long

    GTFS_angl = QgsVectorLayer(GTFSstops_angle_sidewalk_gpkg,'angl_'+str(line_name),'ogr')
    pr = GTFS_angl.dataProvider()
    pr.addAttributes([QgsField("rect_angle", QVariant.Double),
                    QgsField("rect_x2", QVariant.Double),
                    QgsField("rect_y2", QVariant.Double),
                    QgsField("rect_type", QVariant.String)])
    GTFS_angl.updateFields()
    
    expression1 = QgsExpression('azimuth( make_point( "feature_x" ,  "feature_y" ), make_point( "nearest_x" ,  "nearest_y" ) )-1.570796327')
    expression2 = QgsExpression('(("nearest_x" - "feature_x" )*0.60)+ "feature_x"')
    expression3 = QgsExpression('(("nearest_y" - "feature_y" )*0.60)+ "feature_y"')
    
    context = QgsExpressionContext()
    context.appendScopes(QgsExpressionContextUtils.globalProjectLayerScopes(GTFS_angl))

    with edit(GTFS_angl):
        for f in GTFS_angl.getFeatures():
            context.setFeature(f)
            f['rect_angle'] = expression1.evaluate(context)
            f['rect_x2'] = expression2.evaluate(context)
            f['rect_y2'] = expression3.evaluate(context)
            f['rect_type'] = rect_type
            GTFS_angl.updateFeature(f)
    GTFS_angl.commitChanges()

    del context
    
    QgsVectorFileWriter.writeAsVectorFormat(GTFS_angl,GTFSstps_rect_sidewalk_csv,"utf-8",driverName = "CSV")

    # the QgsExpression function doesn't work with sin() function that works on the QGIS FieldCalculator
    GTFS_angldf = pd.read_csv(GTFSstps_rect_sidewalk_csv)
    posXY = trnsprt_long/2
    GTFS_angldf['rect_x'] = GTFS_angldf['rect_x2'] + posXY*np.sin(GTFS_angldf['rect_angle'])
    GTFS_angldf['rect_y'] = GTFS_angldf['rect_y2'] + posXY*np.cos(GTFS_angldf['rect_angle'])

    os.remove(GTFSstps_rect_sidewalk_csv)

    GTFS_angldf.to_csv(GTFSstps_rect_sidewalk_csv,index=False)

    GTFScsvpath = r"file:///{}?crs={}&delimiter={}&xField={}&yField={}".format(GTFSstps_rect_sidewalk_csv,"epsg:4326", ",", "rect_x", "rect_y")
    GTFS_angl_layer = QgsVectorLayer(GTFScsvpath ,'GTFSangl_'+str(line_name),"delimitedtext")

    params = {
        'INPUT': GTFS_angl_layer,
        'SHAPE': 0,
        'WIDTH': QgsProperty.fromExpression('"distance"*1.20'),
        'HEIGHT': trnsprt_long,
        'ROTATION': QgsProperty.fromExpression('degrees("rect_angle")'),
        'SEGMENTS': 36,
        'OUTPUT': GTFSstps_rect_sidewalk_gpkg
        }
    processing.run("native:rectanglesovalsdiamonds", params)

    del params, expression1,expression2,expression3
    # return rectfile, GTFScsv

def rectangles_OSMonROADline(GTFSstops_path_OSMonROADline,buses_long, tram_long, road_average_width,line, GTFSstps_rect_OSMonROADline_gpkg, trnsprt_type):
    
    if trnsprt_type == 'Tram'  or trnsprt_type == 'RegRailServ' or trnsprt_type == 'Funicular' :
        trnsprt_long = tram_long
    else:
        trnsprt_long = buses_long


    long = trnsprt_long*4
    params = {
                'INPUT': str(GTFSstops_path_OSMonROADline),
                'SHAPE': 0,
                'WIDTH': road_average_width,
                'HEIGHT': long,
                'ROTATION': QgsProperty.fromExpression('"nrstrd_stp_angl"'),
                'SEGMENTS': 36,
                'OUTPUT': GTFSstps_rect_OSMonROADline_gpkg
                }
    processing.run("native:rectanglesovalsdiamonds", params)

    rect_type = 'OSMonROADline'
    
    vlayer = QgsVectorLayer(GTFSstps_rect_OSMonROADline_gpkg,'rects_OSMonROADline_'+str(line),'ogr')
    pr = vlayer.dataProvider()
    pr.addAttributes([QgsField("rect_type", QVariant.String)])
    vlayer.updateFields()

    context = QgsExpressionContext()
    context.appendScopes(QgsExpressionContextUtils.globalProjectLayerScopes(vlayer))

    with edit(vlayer):
        for f in vlayer.getFeatures():
            context.setFeature(f)
            f['rect_type'] = rect_type
            vlayer.updateFeature(f)
    vlayer.commitChanges()

    # deleting useless fields in rectfile
    lstodelete = ['stop_lat','stop_lon','location_type','parent_station','OBJECTID','Shape_Length','STR_ESID','nrstrd_stp_angl','n','distance','feature_x','feature_y','nearest_x','nearest_y','layer','path']
       
    idtodelete = [vlayer.fields().indexOf(field_name) for field_name in lstodelete]
    idtodelete = [index for index in idtodelete if index != -1]
    if not vlayer.isEditable():
        vlayer.startEditing()
    res = vlayer.dataProvider().deleteAttributes(idtodelete)
    if res:
        vlayer.updateFields()  # Update the layer's fields
    else:
        print("Failed to delete attributes")
    vlayer.commitChanges()

    del params, lstodelete, idtodelete
    

def OSM_PTstps_dwnld(extent, extent_quickosm,OSM_PTstp_rel_gpkg,OSM_PTstp_gpkg,shrt_name, OSM_PTstp_rel_name, OSM_PTstp_name, trnsprt_type):
    if trnsprt_type == 'Tram':
        route = 'tram'
        route_cond = '"railway" is \'tram_stop\''
    elif trnsprt_type == 'RegRailServ':
        route = 'train'
        route_cond = '"railway" is \'stop\''
    elif trnsprt_type == 'Funicular':
        route = 'funicular'
        route_cond = '"station" is \'funicular\''
    else:
        route = 'bus'
        route_cond = '"highway" is \'bus_stop\''
    
    params = {'QUERY':'[out:xml] [timeout:25];\n(    \n    relation["route"="'+str(route)+'"]["ref"="'+str(shrt_name)+'"]('+str(extent)+');\n);\n(._;>;);\nout body;',
                    'TIMEOUT':180,
                    'SERVER':'https://overpass-api.de/api/interpreter',
                    'EXTENT':extent_quickosm,
                    'AREA':'',
                    'FILE': OSM_PTstp_rel_gpkg}
    try:
        processing.run("quickosm:downloadosmdatarawquery", params )
    except Exception as e:
        print('Overpass API request failed for "server replied Gateway Timeout" -> (skipped)')
        schema = QgsFields()
        schema.append(QgsField('id', QVariant.Int))

        crs = QgsCoordinateReferenceSystem('epsg:4326')
        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = "GPKG"
        options.fileEncoding = 'utf-8'

        fw = QgsVectorFileWriter.create(
            fileName=OSM_PTstp_rel_gpkg,
            fields=schema,
            geometryType=QgsWkbTypes.Polygon,
            srs=crs,
            transformContext=QgsCoordinateTransformContext(),
            options=options)
        del fw

    OSM_PTstp_rel_layer_file = str(OSM_PTstp_rel_gpkg)+'|layername='+str(OSM_PTstp_rel_name)+'_points'
    OSM_PTstp_rel_layer =  QgsVectorLayer(OSM_PTstp_rel_layer_file,OSM_PTstp_name,"ogr")
    
    bus_stops_selection = str(route_cond) +' OR "public_transport" is \'stop_position\''
    params = {'INPUT':OSM_PTstp_rel_layer,
            'EXPRESSION':bus_stops_selection,
            'OUTPUT':OSM_PTstp_gpkg}
    processing.run("native:extractbyexpression", params)
 


def OSMintersecGTFS(rectangles,OSMgpkg,tempOSMfolder, line):
    OSMlayer = QgsVectorLayer(OSMgpkg,'OSM'+str(line),'ogr')
    OSMintersecGTFSgpkg = str(tempOSMfolder)+'/OSMjoinGTFS'+ str(line) +'.gpkg'
    OSMnomatchGTFSgpkg = str(tempOSMfolder)+'/OSM'+str(line) +'_NOmatch.gpkg'
    
    # adding coordinates in the attribute tables for the OSMlayer
    pr = OSMlayer.dataProvider()
    pr.addAttributes([QgsField("lon", QVariant.Double),
                    QgsField("lat", QVariant.Double)])
    OSMlayer.updateFields()
    
    expression1 = QgsExpression('$x')
    expression2 = QgsExpression('$y')
    
    context = QgsExpressionContext()
    context.appendScopes(QgsExpressionContextUtils.globalProjectLayerScopes(OSMlayer))

    with edit(OSMlayer):
        for f in OSMlayer.getFeatures():
            context.setFeature(f)
            f['lon'] = expression1.evaluate(context)
            f['lat'] = expression2.evaluate(context)
            OSMlayer.updateFeature(f)
    OSMlayer.commitChanges()

    # intersecating the GTFS rectangle and the OSM stop position
    params = {'INPUT': OSMlayer,
              'OVERLAY':QgsProcessingFeatureSourceDefinition(rectangles, selectedFeaturesOnly=False, featureLimit=-1, flags=QgsProcessingFeatureSourceDefinition.FlagOverrideDefaultGeometryCheck, geometryCheck=QgsFeatureRequest.GeometrySkipInvalid),
              'INPUT_FIELDS':['full_id','osm_id','lon','lat','osm_type','local_ref','level:ref','ref','old_name','uic_ref','uic_name','public_transport','operator'],
              'OVERLAY_FIELDS':['line_name','trip','pos','stop_id','stop_name','stop_lon','stop_lat','parent_station','prnt_stp_id','stp_pltfrm','route_short_name'],
              'OVERLAY_FIELDS_PREFIX':'GTFS_',
              'OUTPUT':OSMintersecGTFSgpkg,
              'GRID_SIZE':None}
    processing.run("native:intersection", params)

    del params

    params = {'INPUT':OSMlayer,
               'PREDICATE':[0],
               'INTERSECT':rectangles,
               'METHOD':0}
    processing.run("native:selectbylocation", params)
    
    OSMlayer.invertSelection()
    
    _writer = QgsVectorFileWriter.writeAsVectorFormat(OSMlayer,OSMnomatchGTFSgpkg,"utf-8",driverName ="GPKG",onlySelected=True)

    # - saving tables CSV and loading
    OSMjoinGTFSlayer = QgsVectorLayer(OSMintersecGTFSgpkg,'OSMintersecGTFS'+ str(line),'ogr')
    OSMjoinGTFScsv = str(tempOSMfolder)+'/OSMjoinGTFS_'+ str(line)+'.csv'
    QgsVectorFileWriter.writeAsVectorFormat(OSMjoinGTFSlayer,OSMjoinGTFScsv,"utf-8",driverName = "CSV")
    OSMjnGTFS = pd.read_csv(OSMjoinGTFScsv)

    OSMnomatchGTFSlayer = QgsVectorLayer(OSMnomatchGTFSgpkg,'OSM'+str(line) +'_NOmatch','ogr')
    OSMnomatchGTFScsv = str(tempOSMfolder)+'/OSM'+str(line) +'_NOmatch.csv'
    QgsVectorFileWriter.writeAsVectorFormat(OSMnomatchGTFSlayer,OSMnomatchGTFScsv,"utf-8",driverName = "CSV")
    OSMnomatch = pd.read_csv(OSMnomatchGTFScsv)
    del params
    return OSMjnGTFS, OSMnomatch,OSMjoinGTFScsv, OSMnomatchGTFScsv

def stp_posGTFSnm_rect(GTFSnm_rectCSV,line_name,splt_roads,temp_posRCT_folder,buses_long,tram_long, trnsprt_type, agency_txt):

    if trnsprt_type == 'Tram' or trnsprt_type == 'RegRailServ' or trnsprt_type == 'Funicular' :
        trnsprt_long = tram_long
    else:
        trnsprt_long = buses_long
    
    GTFSnm_rect_path = r"file:///{}?crs={}&delimiter={}&xField={}&yField={}".format(GTFSnm_rectCSV,"epsg:4326", ",", "stop_lon", "stop_lat")
    GTFSnm_rect_layer = QgsVectorLayer(GTFSnm_rect_path,'GTFSNMrect_'+str(line_name) ,"delimitedtext")
    
    GTFS_nmRCT_pos_CSV1 = str(temp_posRCT_folder)+'/GTFSnmRCT_pos_'+str(line_name)+'_1.csv'
    GTFS_nmRCT_pos_CSV2 = str(temp_posRCT_folder)+'/GTFSnmRCT_pos_'+str(line_name)+'_2.csv'
    GTFS_nmRCT_pos_CSV3 = str(temp_posRCT_folder)+'/GTFSnmRCT_pos_'+str(line_name)+'_3.csv'
    GTFS_nmRCT_NEWpos_CSV = str(temp_posRCT_folder)+'/GTFSnmRCT_pos_'+str(line_name)+'.csv'
    GTFS_pos1  = str(temp_posRCT_folder)+'/GTFSnmRCT_pos_'+str(line_name)+'_1.gpkg'
    GTFS_pos  = str(temp_posRCT_folder)+'/GTFSnmRCT_pos_'+str(line_name)+'.gpkg'
    
    params = {'INPUT':GTFSnm_rect_layer,
            'INPUT_2':splt_roads,
            'FIELDS_TO_COPY':['full_id','osm_id','osm_type','name','highway'],
            'DISCARD_NONMATCHING':True,
            'PREFIX':'nrstrd_',
            'NEIGHBORS':1,
            'MAX_DISTANCE':0.00015,
            'OUTPUT':GTFS_pos1}
    processing.run("native:joinbynearest", params)

    

    GTFS_posangl = QgsVectorLayer(GTFS_pos1,'GTFSnmRCT_posangl_'+str(line_name) ,"ogr")
    
    pr = GTFS_posangl.dataProvider()
    pr.addAttributes([QgsField("pos_angl", QVariant.Double)])
    GTFS_posangl.updateFields()
    
    expression1 = QgsExpression('azimuth( make_point( "feature_x" ,  "feature_y" ), make_point( "nearest_x" ,  "nearest_y" ) )-1.570796327')
    
    context = QgsExpressionContext()
    context.appendScopes(QgsExpressionContextUtils.globalProjectLayerScopes(GTFS_posangl))

    with edit(GTFS_posangl):
        for f in GTFS_posangl.getFeatures():
            context.setFeature(f)
            f['pos_angl'] = expression1.evaluate(context)
            GTFS_posangl.updateFeature(f)
    GTFS_posangl.commitChanges()

    del context

    QgsVectorFileWriter.writeAsVectorFormat(GTFS_posangl,GTFS_nmRCT_pos_CSV1 ,"utf-8",driverName = "CSV")
    # QgsVectorFileWriter.writeAsVectorFormat(GTFS_posangl,GTFScsv,"utf-8",driverName = "CSV")


    # calculate the angle of the new stop_position
    # the QgsExpression function doesn't work with sin() function that works on the QGIS FieldCalculator
    GTFS_angldf = pd.read_csv(GTFS_nmRCT_pos_CSV1)
    posXY = trnsprt_long/2
    GTFS_angldf['pos_x2'] = GTFS_angldf['stop_lon'] + posXY*np.sin(GTFS_angldf['pos_angl'])
    GTFS_angldf['pos_y2'] = GTFS_angldf['stop_lat'] + posXY*np.cos(GTFS_angldf['pos_angl'])
    
    agency = pd.read_csv(agency_txt)
    ls_agency = agency.agency_id.unique()
    i_row = 0
    while i_row < len(GTFS_angldf):
        if GTFS_angldf.loc[i_row,'distance'] < 0.00001 or not 881 in ls_agency:
            GTFS_angldf.loc[i_row,'pos_x2'] = GTFS_angldf.loc[i_row,'feature_x']
            GTFS_angldf.loc[i_row,'pos_y2'] = GTFS_angldf.loc[i_row,'feature_y']
        i_row += 1
    
    ls_to_delete = ['distance','feature_x','feature_y','nearest_x','nearest_y','nrstrd_full_id','nrstrd_osm_id','nrstrd_osm_type','nrstrd_name','nrstrd_highway','n']
    exist_cols = GTFS_angldf.columns
    ls_to_drop = [col for col in ls_to_delete if col in exist_cols]
    GTFS_angldf = GTFS_angldf.drop(ls_to_drop, axis=1)

    

    GTFS_angldf.to_csv(GTFS_nmRCT_pos_CSV2, index=False)
    GTFS_angl_pos_path = r"file:///{}?crs={}&delimiter={}&xField={}&yField={}".format(GTFS_nmRCT_pos_CSV2,"epsg:4326", ",", "pos_x2", "pos_y2")
    GTFS_angl_pos = QgsVectorLayer(GTFS_angl_pos_path,'angl_pos_'+str(line_name),"delimitedtext")
    
    params = {'INPUT':GTFS_angl_pos,
            'INPUT_2':splt_roads,
            'FIELDS_TO_COPY':['full_id','osm_id','osm_type','name','highway'],
            'DISCARD_NONMATCHING':True,
            'PREFIX':'nrstrd_',
            'NEIGHBORS':1,
            'MAX_DISTANCE':0.00015,
            'OUTPUT':GTFS_pos}
    processing.run("native:joinbynearest", params)
    
    GTFS_pos_layer = QgsVectorLayer(GTFS_pos,'GTFSnmRCT_'+str(line_name),'ogr')
    QgsVectorFileWriter.writeAsVectorFormat(GTFS_pos_layer,GTFS_nmRCT_pos_CSV3 ,"utf-8",driverName = "CSV")

    GTFS_posdf = pd.read_csv(GTFS_nmRCT_pos_CSV3)

    ls_to_delete = ['distance','feature_x','feature_y','pos_x2','pos_y2']
    exist_cols = GTFS_posdf.columns
    ls_to_drop = [col for col in ls_to_delete if col in exist_cols]
    GTFS_posdf = GTFS_posdf.drop(ls_to_drop, axis=1)
    GTFS_posdf = GTFS_posdf.rename(columns={'nearest_x':'lon','nearest_y':'lat'})
    
    
    GTFS_posdf.to_csv(GTFS_nmRCT_NEWpos_CSV, index=False)
    
    os.remove(GTFS_nmRCT_pos_CSV1)
    os.remove(GTFS_nmRCT_pos_CSV2)
    os.remove(GTFS_nmRCT_pos_CSV3)
    os.remove(GTFS_pos1)

    return GTFS_nmRCT_NEWpos_CSV

def joinNEWandValidOSM(newOSMpos,GTFSnomatch_RD,OSMintersectGTFS,GTFSstps_seg,temp_OSM_for_routing,line,stops_txt):
    
    GTFSnm = pd.read_csv(GTFSnomatch_RD,dtype = {'stop_id': str})
    validOSM = pd.read_csv(OSMintersectGTFS)
    GTFSss = pd.read_csv(GTFSstps_seg)
    OSMstops_unsorted = pd.DataFrame()

    if os.path.exists(newOSMpos):
        newOSM = pd.read_csv(newOSMpos,dtype = {'stop_id': str})
        newOSM = newOSM[['stop_id','line_name','trip','pos','lon','lat']]
        newOSM['loc_base'] = 'generated from GTFS on OSM roads'
        newOSM = newOSM.rename(columns={'stop_id':'GTFS_stop_id'})
        OSMstops_unsorted = pd.concat([OSMstops_unsorted , newOSM], ignore_index=True)

    if not GTFSnm.empty:
        GTFSnm = GTFSnm[['stop_id','line_name','trip','pos','stop_lon','stop_lat']]
        GTFSnm['loc_base'] = 'GTFS points'
        GTFSnm = GTFSnm.rename(columns={'stop_id':'GTFS_stop_id','stop_lat':'lat','stop_lon':'lon'})
        OSMstops_unsorted = pd.concat([OSMstops_unsorted , GTFSnm], ignore_index=True)

    if not validOSM.empty:
        validOSM = validOSM[['GTFS_stop_id','GTFS_line_name','GTFS_trip','GTFS_pos','lon','lat']]
        validOSM['loc_base'] = 'already present on OSM'
        validOSM = validOSM.rename(columns={'GTFS_trip':'trip','GTFS_pos':'pos','GTFS_line_name':'line_name'})
        OSMstops_unsorted = pd.concat([OSMstops_unsorted , validOSM], ignore_index=True)

    
    OSMstops_updated = OSMstops_unsorted.sort_values(['trip','pos']).reset_index(drop=True)

    # if there is more than one stop in OSM per GTFS
    # few lines later the closer OSM is taken !!!
    if len(GTFSss) == len(OSMstops_updated):
        print('for each GTFS there is an OSM in the '+str(line)+' line ')
    else:
        print('in the '+str(line)+' line, for some GTFS there are more than one OSM, the closest OSM has been kept')
    
    i_row = 0
    while i_row<len(OSMstops_updated):
        OSMstops_updated.loc[i_row, 'line_trip'] = str(OSMstops_updated.loc[i_row, 'line_name'])+'_trip'+str(OSMstops_updated.loc[i_row, 'trip'])
        i_row += 1 
    ls_trips = OSMstops_updated.line_trip.unique()
    

    stops = pd.read_csv(stops_txt,dtype = {'stop_id': str})
    OSMstops_updated = OSMstops_updated.astype({'GTFS_stop_id':'str'})
    stops = stops[['stop_id','stop_lon','stop_lat']]
    OSMstops_updated = OSMstops_updated.merge(stops,how='left', left_on='GTFS_stop_id', right_on='stop_id')

    # in case there is more than one OSM stop for an GTFS,
    # the farest is deleted 
    todelete = []
    i_row = 0
    i_row2 = 1
    while i_row2 < len(OSMstops_updated):
        if OSMstops_updated.loc[i_row,'pos'] == OSMstops_updated.loc[i_row2,'pos']:
            dist1 = math.sqrt(((OSMstops_updated.loc[i_row,'lon']-OSMstops_updated.loc[i_row,'stop_lon'])**2) + ((OSMstops_updated.loc[i_row,'lat']-OSMstops_updated.loc[i_row,'stop_lat'])**2))
            dist2 = math.sqrt(((OSMstops_updated.loc[i_row2,'lon']-OSMstops_updated.loc[i_row2,'stop_lon'])**2) + ((OSMstops_updated.loc[i_row2,'lat']-OSMstops_updated.loc[i_row2,'stop_lat'])**2))
            if dist1 < dist2:
                todelete.append(i_row2)
            else:
                todelete.append(i_row)
        i_row += 1
        i_row2 += 1

    OSMstops_tosave = OSMstops_updated.drop(todelete).reset_index(drop=True)
    
    OSMstops_tosave = OSMstops_tosave.drop(["stop_lon","stop_lat"],axis=1)
    for trip in ls_trips:
        OSMstops_trip = OSMstops_tosave[OSMstops_tosave['line_trip'] == trip]
        OSMstops_trip_csv = str(temp_OSM_for_routing)+'/OSM4routing_'+str(trip)+'.csv'
        OSMstops_trip_gpkg = str(temp_OSM_for_routing)+'/OSM4routing_'+str(trip)+'.gpkg'
        OSMstops_trip.to_csv(OSMstops_trip_csv, index=False)
        OSM4rout_path = r"file:///{}?crs={}&delimiter={}&xField={}&yField={}&field=trip:integer".format(OSMstops_trip_csv,"EPSG:4326", ",", "lon", "lat")
        OSM4rout_layer = QgsVectorLayer(OSM4rout_path,"OSM_for_routing","delimitedtext")
        QgsVectorFileWriter.writeAsVectorFormat(OSM4rout_layer, OSMstops_trip_gpkg, "UTF-8", OSM4rout_layer.crs(), "GPKG")
        os.remove(OSMstops_trip_csv)
            
    OSMstops_forrouting = str(temp_OSM_for_routing)+'/OSM4routing_'+str(line)+'.csv'
    OSMstops_tosave.to_csv(OSMstops_forrouting, index = False)
    return OSMstops_forrouting

# to attach at the end of the stops correctly visualized on the map
# to finish

def display_vector_layer(OSMcheckedstops_layer):
    QgsProject.instance().addMapLayer(OSMcheckedstops_layer)
    

def zoom_to_layer(OSMcheckedsotps_layer):
    canvas = iface.mapCanvas()
    extent = OSMcheckedsotps_layer.extent()
    canvas.setExtent(extent)
    canvas.refresh()

def transcript_main_files(main_files_fld,main_files_csv,OSM_ways_name,OSM_ways_gpkg,OSM_roads_name,OSM_roads_gpkg,OSM_roads_nameCSV,OSM_roads_csv,highway_speed_name,highway_speed_csv, bus_lanes_name, OSM_bus_lanes_gpkg,full_roads_name, full_roads_gpgk, Ttbls_selected_name,Ttbls_selected_txt):
    main_files = pd.DataFrame()
    
    i_row = len(main_files)
    main_files.loc[i_row,'file_name'] = OSM_ways_name
    main_files.loc[i_row,'file_path'] = OSM_ways_gpkg

    i_row = len(main_files)
    main_files.loc[i_row,'file_name'] = OSM_roads_name
    main_files.loc[i_row,'file_path'] = OSM_roads_gpkg

    i_row = len(main_files)
    main_files.loc[i_row,'file_name'] = OSM_roads_nameCSV
    main_files.loc[i_row,'file_path'] = OSM_roads_csv

    i_row = len(main_files)
    main_files.loc[i_row,'file_name'] = highway_speed_name
    main_files.loc[i_row,'file_path'] = highway_speed_csv

    i_row = len(main_files)
    main_files.loc[i_row,'file_name'] = bus_lanes_name
    main_files.loc[i_row,'file_path'] = OSM_bus_lanes_gpkg

    i_row = len(main_files)
    main_files.loc[i_row,'file_name'] = full_roads_name
    main_files.loc[i_row,'file_path'] = full_roads_gpgk


    i_row = len(main_files)
    main_files.loc[i_row,'file_name'] = Ttbls_selected_name
    main_files.loc[i_row,'file_path'] = Ttbls_selected_txt

    os.makedirs(main_files_fld)
    main_files.to_csv(main_files_csv,index=False)
    return main_files

def if_display(file_path,layer_name):
    if os.path.exists(file_path):
        if not QgsProject.instance().mapLayersByName(layer_name):
            city_r_layer = QgsVectorLayer(file_path,layer_name,"ogr")
            QgsProject.instance().addMapLayer(city_r_layer)