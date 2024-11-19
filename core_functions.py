from qgis import processing
from qgis.core import QgsVectorLayer, QgsField, QgsExpressionContext, QgsExpressionContextUtils, edit, QgsExpression, QgsCoordinateReferenceSystem
from qgis.PyQt.QtCore import QVariant
import pandas as pd
import re

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

def full_city_roads(OSM_roads_gpkg,bus_lanes_gpkg, full_roads_gpgk):
    city_name = 'city roads'
    road_layer = QgsVectorLayer(OSM_roads_gpkg,city_name,"ogr")
    
    pr = road_layer.dataProvider()
    pr.addAttributes([QgsField("oneway_routing", QVariant.String),
                      QgsField("maxspeed_routing", QVariant.Int)])
    road_layer.updateFields()

    expression1 = QgsExpression('IF("oneway" is \'yes\',\'forward\',NULL)')
    expression2 = QgsExpression('if("maxspeed" is not NULL AND regexp_match("maxspeed",\'[0-9]+\'), "maxspeed", if("highway" is \'residential\' , \'34\' , IF("highway" is \'motorway\' , \'103\' , IF("highway" is \'motorway_link\' , \'65\', IF("highway" is \'tertiary\' , \'48\' , IF("highway" is \'unclassified\' , \'44\', IF("highway" is \'trunk_link\' , \'78\', IF("highway" is \'primary\' , \'57\', IF("highway" is \'secondary\' , \'53\', IF("highway" is \'service\' , \'28\', IF("highway" is \'primary_link\' , \'52\', IF("highway" is \'trunk\' , \'108\', IF("highway" is \'tertiary_link\' , \'49\' , IF("highway" is \'secondary_link\' , \'49\', IF("highway" is \'living_street\' , \'20\' , \'50\' )))))))))))))))')

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