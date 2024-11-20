from qgis import processing
from qgis.core import QgsProperty, QgsVectorFileWriter, QgsVectorLayer, QgsField, QgsExpressionContext, QgsExpressionContextUtils, edit, QgsExpression, QgsCoordinateReferenceSystem, QgsProcessingFeatureSourceDefinition,QgsFeatureRequest, QgsProject
from qgis.utils import iface
from qgis.PyQt.QtCore import QVariant
import pandas as pd
import re
import numpy as np
import os

import statistics as stat

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

def busroutes(bus_lanes_name, OSM_bus_lanes_gpkg,OSM_roads_gpkg):

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
    expression2 = QgsExpression('if("maxspeed" is not NULL AND regexp_match("maxspeed",\'[0-9]+\'), "maxspeed"*\'2\', if("highway" = \'residential\',\'68\', if("highway" = \'motorway\',\'207\', if("highway" = \'motorway_link\',\'131\', if("highway" = \'tertiary\',\'96\', if("highway" = \'unclassified\',\'88\', if("highway" = \'trunk_link\',\'156\', if("highway" = \'primary\',\'114\', if("highway" = \'secondary\',\'106\', if("highway" = \'service\',\'55\', if("highway" = \'primary_link\',\'106\', if("highway" = \'trunk\',\'215\', if("highway" = \'tertiary_link\',\'98\', if("highway" = \'secondary_link\',\'100\', if("highway" = \'living_street\',\'40\',\'70\')))))))))))))))')

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

def full_city_roads(OSM_roads_gpkg,bus_lanes_gpkg, full_roads_gpgk, city_roads_name):
    
    road_layer = QgsVectorLayer(OSM_roads_gpkg,city_roads_name,"ogr")
    
    pr = road_layer.dataProvider()
    pr.addAttributes([QgsField("oneway_routing", QVariant.String),
                      QgsField("maxspeed_routing", QVariant.Int)])
    road_layer.updateFields()

    expression1 = QgsExpression('IF("oneway" is \'yes\',\'forward\',NULL)')
    expression2 = QgsExpression('if("maxspeed" is not NULL AND regexp_match("maxspeed",\'[0-9]+\'), "maxspeed", if("highway" = \'residential\',\'34\', if("highway" = \'motorway\',\'103\', if("highway" = \'motorway_link\',\'75\', if("highway" = \'tertiary\',\'48\', if("highway" = \'unclassified\',\'44\', if("highway" = \'trunk_link\',\'78\', if("highway" = \'primary\',\'57\', if("highway" = \'secondary\',\'53\', if("highway" = \'service\',\'27\', if("highway" = \'primary_link\',\'53\', if("highway" = \'trunk\',\'117\', if("highway" = \'tertiary_link\',\'49\', if("highway" = \'secondary_link\',\'50\', if("highway" = \'living_street\',\'20\',\'50\')))))))))))))))')

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

def Selected_Ttbls(ls_buses,Ttbls_selected_txt,Ttlbs_txt, dwnldfld):
    Ttbls = pd.read_csv(Ttlbs_txt)
    Ttbls['prnt_stp_id']= ""

    i_row = 0

    #calculate the parent_stop_id in Ttbls
    while i_row < len(Ttbls):
        Ttbls.loc[i_row,'prnt_stp_id'] = str(Ttbls.loc[i_row,'stop_id'][:7])
        i_row=i_row+1

    i_row = 0

    # merge route_id
    trips = pd.read_csv(str(dwnldfld)+'/trips.txt')
    trps = trips[['trip_id','route_id']]
    Ttbls = pd.merge(Ttbls,trps,on='trip_id', how='left')
    
    #join the route_short_name 
    routes = pd.read_csv(str(dwnldfld)+'/routes.txt')
    rts = routes.filter(['route_id','route_short_name'],axis=1)

    Ttbls = Ttbls.merge(rts,on='route_id', how='left')
    
    Ttbls_selected = Ttbls[Ttbls['route_short_name'].isin(ls_buses) ]

    Ttbls_selected.to_csv(Ttbls_selected_txt, index=False)

def time_tables_perTransport(rt,Ttbls,tempfldr,lstrnsprt,trnsprt_type ):
    
    Ttbl = Ttbls[Ttbls.route_id == rt]
    num = str(Ttbl['route_short_name'].iloc[0])
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
    i_row = 0
    while i_row < len(Ttbl):
        if Ttbl.loc[i_row, 'stop_id'][-1:].isnumeric():
            Ttbl.loc[i_row, 'stp_pltfrm'] = ''
        else:
            Ttbl.loc[i_row, 'stp_pltfrm'] = Ttbl.loc[i_row, 'stop_id'][-1:]
        i_row += 1
    
    Ttbl_file = str(tempfldr)+'/'+str(nametbl)+'_stop_times.csv'
    Ttbl.to_csv(Ttbl_file, index=False)
    rt_srt_nm = str(Ttbl['route_short_name'].iloc[0])
    return Ttbl, nametbl, Ttbl_file, rt_srt_nm

    
def preapare_GTFSstops_by_transport(stps, Ttbl_file,trnsprt,tempfolder,shrt_name):
    
    #load the stop times (Time Table) ot the transport
    Ttbl_unsorted = pd.read_csv(Ttbl_file)
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
            seq_ls.append(Ttbl.loc[i_row,'prnt_stp_id'])
            seq_end += 1
        else:
            seq_ls.append(Ttbl.loc[i_row,'prnt_stp_id'])
            seq_str = str(seq_ls[0])
            # add the sequence to the Ttbl
            i_ls = 1
            while i_ls < len(seq_ls):
                seq_str = str(seq_str) +' '+str(seq_ls[i_ls])
                i_ls +=1
            sequences.loc[i_seq,0] = i_seq
            sequences.loc[i_seq,'sequence'] = seq_str
            i_seq += 1
            while seq_init <= seq_end:
                Ttbl.loc[seq_init,'sequence'] = seq_str
                seq_init += 1
            del seq_ls, i_ls, seq_str
            seq_ls = []
            seq_end += 1
        i_row +=1
        i_row2 +=1

    # add the sequence to the record of the last sequence >bug resolved<
    seq_ls.append(Ttbl.loc[i_row,'prnt_stp_id'])
    seq_str = str(seq_ls[0])
    i_ls = 1
    while i_ls < len(seq_ls):
        seq_str = str(seq_str) +' '+str(seq_ls[i_ls])
        i_ls +=1
    sequences.loc[i_seq,0] = i_seq
    sequences.loc[i_seq,'sequence'] = seq_str
    del i_seq
    while seq_init <= seq_end:
        Ttbl.loc[seq_init,'sequence'] = seq_str
        seq_init += 1
    del seq_ls, i_ls, seq_str

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
        i_row2 = 0
        while i_row2 < len(Ttbl):
            if Ttbl.loc[i_row2,'sequence'] in mother_sequences[i_row]:
                Ttbl.loc[i_row2,'seq_stpID'] = str(trnsprt)+'_main'+str(i_row+1)+'_pos'+str(mother_sequences[i_row].split().index(str(Ttbl.loc[i_row2,'prnt_stp_id'])))
            i_row2 += 1
        i_row += 1



    i_row = 0
    while i_row < len(Ttbl):
        Ttbl.loc[i_row,'trip'] = int(Ttbl.loc[i_row,'seq_stpID'].split('_')[1][4:])
        Ttbl.loc[i_row,'pos'] = int(Ttbl.loc[i_row,'seq_stpID'].split('_')[2][3:])
        i_row += 1
    Ttbl = Ttbl.astype({'trip':'int','pos':'int'})

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
            most_freq_stps.loc[i_row, 'mini_tr_pos'] = str(trnsprt)+'_main'+str(most_freq_stps.loc[i_row, 'trip'])+'_pos'+str((most_freq_stps.loc[i_row, 'pos']))+'-pos'+str((most_freq_stps.loc[i_row2, 'pos']))
        i_row += 1
        i_row2 += 1


    
    most_freq_stps = most_freq_stps.merge (stps, how='left', on='stop_id') 

    i=0

    # calculate the parent_stop_id in transport stops table
    while i < len(most_freq_stps):
        most_freq_stps.loc[i,'prnt_stp_id'] = str(most_freq_stps.loc[i,'stop_id'][:7])
        i=i+1
    del i
    i=0
    
    # calculate the stp_pltfrm in Ttbls
    while i < len(most_freq_stps):
        if str(most_freq_stps.loc[i,'stop_id'][-1:]).isnumeric():
            most_freq_stps.loc[i,'stp_pltfrm'] = ""
        else:
            most_freq_stps.loc[i,'stp_pltfrm'] = str(most_freq_stps.loc[i,'stop_id'][-1:])
        i=i+1
    most_freq_stps['line_name'] = trnsprt
    
    most_freq_stps['route_short_name'] = shrt_name
    

    GTFSstops_path = str(tempfolder)+'/'+str(trnsprt)+'_stops_segments.csv'
    most_freq_stps.to_csv(GTFSstops_path, index =False)
    return GTFSstops_path

def angles(roadlayer,trnsprt,trnsprt_GTFSstops_file,temp_road_folder,GTFSnm_folder):
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
    
    anglefile = str(temp_road_folder)+'/GTFS'+str(trnsprt)+'_anlge.gpkg'
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

def rectangles_bus(stops_angls, trnsprt_long,temp_folder, trnsprt):
    GTFScsv = str(temp_folder)+'/GTFSangl_'+str(trnsprt)+'.csv'
    rectfile = str(temp_folder)+'/rects_'+str(trnsprt)+'.gpkg'

    GTFS_angl = QgsVectorLayer(stops_angls,'angl_'+str(trnsprt),'ogr')
    pr = GTFS_angl.dataProvider()
    pr.addAttributes([QgsField("rect_angle", QVariant.Double),
                    QgsField("rect_x2", QVariant.Double),
                    QgsField("rect_y2", QVariant.Double)])
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
            GTFS_angl.updateFeature(f)
    GTFS_angl.commitChanges()

    del context
    
    QgsVectorFileWriter.writeAsVectorFormat(GTFS_angl,GTFScsv,"utf-8",driverName = "CSV")

    # the QgsExpression function doesn't work with sin() function that works on the QGIS FieldCalculator
    GTFS_angldf = pd.read_csv(GTFScsv)
    posXY = trnsprt_long/2
    GTFS_angldf['rect_x'] = GTFS_angldf['rect_x2'] + posXY*np.sin(GTFS_angldf['rect_angle'])
    GTFS_angldf['rect_y'] = GTFS_angldf['rect_y2'] + posXY*np.cos(GTFS_angldf['rect_angle'])

    os.remove(GTFScsv)

    GTFS_angldf.to_csv(GTFScsv,index=False)

    GTFScsvpath = r"file:///{}?crs={}&delimiter={}&xField={}&yField={}".format(GTFScsv,"epsg:4326", ",", "rect_x", "rect_y")
    GTFS_angl_layer = QgsVectorLayer(GTFScsvpath ,'GTFSangl_'+str(trnsprt),"delimitedtext")

    params = {
        'INPUT': GTFS_angl_layer,
        'SHAPE': 0,
        'WIDTH': QgsProperty.fromExpression('"distance"*1.20'),
        'HEIGHT': trnsprt_long,
        'ROTATION': QgsProperty.fromExpression('degrees("rect_angle")'),
        'SEGMENTS': 36,
        'OUTPUT': rectfile
        }
    processing.run("native:rectanglesovalsdiamonds", params)

    del params, expression1,expression2,expression3
    return rectfile, GTFScsv

def OSM_PTstps_dwnld(extent, extent_quickosm,OSM_PTstp_rel_gpkg,OSM_PTstp_gpkg,shrt_name, OSM_PTstp_rel_name, OSM_PTstp_name):
    params = {'QUERY':'[out:xml] [timeout:25];\n(    \n    relation["route"="bus"]["ref"="'+str(shrt_name)+'"]('+str(extent)+');\n);\n(._;>;);\nout body;',
                    'TIMEOUT':180,
                    'SERVER':'https://overpass-api.de/api/interpreter',
                    'EXTENT':extent_quickosm,
                    'AREA':'',
                    'FILE': OSM_PTstp_rel_gpkg}
    processing.run("quickosm:downloadosmdatarawquery", params )
    
    OSM_PTstp_rel_layer_file = str(OSM_PTstp_rel_gpkg)+'|layername='+str(OSM_PTstp_rel_name)+'_points'
    OSM_PTstp_rel_layer =  QgsVectorLayer(OSM_PTstp_rel_layer_file,OSM_PTstp_name,"ogr")
    
    bus_stops_selection = '"highway" is \'bus_stop\' OR "public_transport" is \'stop_position\''
    params = {'INPUT':OSM_PTstp_rel_layer,
            'EXPRESSION':bus_stops_selection,
            'OUTPUT':OSM_PTstp_gpkg}
    processing.run("native:extractbyexpression", params)
 


def OSMintersecGTFS(rectangles,OSMgpkg,tempOSMfolder,shrt_name):
    OSMlayer = QgsVectorLayer(OSMgpkg,'OSM'+str(shrt_name),'ogr')
    OSMintersecGTFSgpkg = str(tempOSMfolder)+'/OSMjoinGTFS'+ str(shrt_name) +'.gpkg'
    OSMnomatchGTFSgpkg = str(tempOSMfolder)+'/OSM'+str(shrt_name) +'_NOmatch.gpkg'
    
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
    OSMjoinGTFSlayer = QgsVectorLayer(OSMintersecGTFSgpkg,'OSMintersecGTFS'+ str(shrt_name),'ogr')
    OSMjoinGTFScsv = str(tempOSMfolder)+'/OSMjoinGTFS_'+ str(shrt_name)+'.csv'
    QgsVectorFileWriter.writeAsVectorFormat(OSMjoinGTFSlayer,OSMjoinGTFScsv,"utf-8",driverName = "CSV")
    OSMjnGTFS = pd.read_csv(OSMjoinGTFScsv)

    OSMnomatchGTFSlayer = QgsVectorLayer(OSMnomatchGTFSgpkg,'OSM'+str(shrt_name) +'_NOmatch','ogr')
    OSMnomatchGTFScsv = str(tempOSMfolder)+'/OSM'+str(shrt_name) +'_NOmatch.csv'
    QgsVectorFileWriter.writeAsVectorFormat(OSMnomatchGTFSlayer,OSMnomatchGTFScsv,"utf-8",driverName = "CSV")
    OSMnomatch = pd.read_csv(OSMnomatchGTFScsv)
    del params
    return OSMjnGTFS, OSMnomatch,OSMjoinGTFScsv, OSMnomatchGTFScsv

def stp_posGTFSnm_rect(GTFSnm_rectCSV,trnsprt,splt_roads,temp_posRCT_folder,trnsprt_long):
    GTFSnm_rect_path = r"file:///{}?crs={}&delimiter={}&xField={}&yField={}".format(GTFSnm_rectCSV,"epsg:4326", ",", "stop_lon", "stop_lat")
    GTFSnm_rect_layer = QgsVectorLayer(GTFSnm_rect_path,'GTFSNMrect_'+str(trnsprt) ,"delimitedtext")

    
    GTFS_nmRCT_pos_CSV1 = str(temp_posRCT_folder)+'/GTFSnmRCT_pos_'+str(trnsprt)+'_1.csv'
    GTFS_nmRCT_pos_CSV2 = str(temp_posRCT_folder)+'/GTFSnmRCT_pos_'+str(trnsprt)+'_2.csv'
    GTFS_nmRCT_pos_CSV3 = str(temp_posRCT_folder)+'/GTFSnmRCT_pos_'+str(trnsprt)+'_3.csv'
    GTFS_nmRCT_NEWpos_CSV = str(temp_posRCT_folder)+'/GTFSnmRCT_pos_'+str(trnsprt)+'.csv'
    GTFS_pos1  = str(temp_posRCT_folder)+'/GTFSnmRCT_pos_'+str(trnsprt)+'_1.gpkg'
    GTFS_pos  = str(temp_posRCT_folder)+'/GTFSnmRCT_pos_'+str(trnsprt)+'.gpkg'
    
    params = {'INPUT':GTFSnm_rect_layer,
            'INPUT_2':splt_roads,
            'FIELDS_TO_COPY':['full_id','osm_id','osm_type','name','highway'],
            'DISCARD_NONMATCHING':True,
            'PREFIX':'nrstrd_',
            'NEIGHBORS':1,
            'MAX_DISTANCE':0.00015,
            'OUTPUT':GTFS_pos1}
    processing.run("native:joinbynearest", params)

    

    GTFS_posangl = QgsVectorLayer(GTFS_pos1,'GTFSnmRCT_posangl_'+str(trnsprt) ,"ogr")
    
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
    
    GTFS_angldf = GTFS_angldf.drop(['distance','feature_x','feature_y','nearest_x','nearest_y','nrstrd_full_id','nrstrd_osm_id','nrstrd_osm_type','nrstrd_name','nrstrd_highway','n'], axis=1)

    

    GTFS_angldf.to_csv(GTFS_nmRCT_pos_CSV2, index=False)
    GTFS_angl_pos_path = r"file:///{}?crs={}&delimiter={}&xField={}&yField={}".format(GTFS_nmRCT_pos_CSV2,"epsg:4326", ",", "pos_x2", "pos_y2")
    GTFS_angl_pos = QgsVectorLayer(GTFS_angl_pos_path,'angl_pos_'+str(trnsprt),"delimitedtext")
    
    params = {'INPUT':GTFS_angl_pos,
            'INPUT_2':splt_roads,
            'FIELDS_TO_COPY':['full_id','osm_id','osm_type','name','highway'],
            'DISCARD_NONMATCHING':True,
            'PREFIX':'nrstrd_',
            'NEIGHBORS':1,
            'MAX_DISTANCE':0.00015,
            'OUTPUT':GTFS_pos}
    processing.run("native:joinbynearest", params)
    
    GTFS_pos_layer = QgsVectorLayer(GTFS_pos,'GTFSnmRCT_'+str(trnsprt),'ogr')
    QgsVectorFileWriter.writeAsVectorFormat(GTFS_pos_layer,GTFS_nmRCT_pos_CSV3 ,"utf-8",driverName = "CSV")

    GTFS_posdf = pd.read_csv(GTFS_nmRCT_pos_CSV3)
    GTFS_posdf = GTFS_posdf.drop(['distance','feature_x','feature_y','pos_x2','pos_y2'], axis=1)
    GTFS_posdf = GTFS_posdf.rename(columns={'nearest_x':'lon','nearest_y':'lat'})
    
    
    GTFS_posdf.to_csv(GTFS_nmRCT_NEWpos_CSV, index=False)
    
    os.remove(str(GTFS_nmRCT_pos_CSV1))
    os.remove(str(GTFS_nmRCT_pos_CSV2))
    os.remove(str(GTFS_nmRCT_pos_CSV3))
    os.remove(str(GTFS_pos1))

    return GTFS_nmRCT_NEWpos_CSV

def joinNEWandValidOSM(newOSMpos,GTFSnomatch_RD,OSMintersectGTFS,GTFSstps_seg,temp_OSM_for_routing,line):
    newOSM = pd.read_csv(newOSMpos)
    GTFSnm = pd.read_csv(GTFSnomatch_RD)
    validOSM = pd.read_csv(OSMintersectGTFS)
    GTFSss = pd.read_csv(GTFSstps_seg)

    newOSM = newOSM[['stop_id','line_name','trip','pos','lon','lat']]
    newOSM['loc_base'] = 'generated from GTFS on OSM roads'
    newOSM = newOSM.rename(columns={'stop_id':'GTFS_stop_id'})

    GTFSnm = GTFSnm[['stop_id','line_name','trip','pos','stop_lon','stop_lat']]
    GTFSnm['loc_base'] = 'GTFS points'
    GTFSnm = GTFSnm.rename(columns={'stop_id':'GTFS_stop_id','stop_lat':'lat','stop_lon':'lon'})
    

    validOSM = validOSM[['GTFS_stop_id','GTFS_line_name','GTFS_trip','GTFS_pos','lon','lat']]
    validOSM['loc_base'] = 'already present on OSM'
    validOSM = validOSM.rename(columns={'GTFS_trip':'trip','GTFS_pos':'pos','GTFS_line_name':'line_name'})
    

    OSMstops_unsorted = pd.concat([validOSM,newOSM,GTFSnm], ignore_index=True)
    OSMstops_updated = OSMstops_unsorted.sort_values(['trip','pos']).reset_index(drop=True)

    if len(GTFSss) == len(OSMstops_updated):
        print('for each GTFS there is an OSM')
    else:
        print('incoerence in the number of GTFS with the OSM')
    OSMstops_forrouting = str(temp_OSM_for_routing)+'/OSM4routing_'+str(line)+'.csv'
    OSMstops_updated.to_csv(OSMstops_forrouting, index=False)
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