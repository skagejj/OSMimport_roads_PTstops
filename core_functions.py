from qgis import processing
from qgis.core import QgsVectorLayer, QgsField, QgsExpressionContext, QgsExpressionContextUtils, edit, QgsExpression

def busroutes(OSM_roads_gpkg,temp_folder):

    bus_lanes_name = 'OSM_bus_lanes'
    OSM_bus_lanes_gpkg = str(temp_folder)+'/'+str(bus_lanes_name)+'.gpkg'
    bus_lanes_selection = '"bus" is not NULL OR "bus:lanes" is not NULL   OR "bus:lanes:backward" is not NULL OR "bus:lanes:forward" is not NULL OR "busway" is not NULL OR "busway:left" is not NULL OR "busway:left" is not NULL   OR "busway:right" is not NULL OR "busway:right" is not NULL   OR "hgv" is not NULL OR "hgv:lanes" is not NULL OR "lanes:bus" is not NULL OR "lanes:bus:backward" is not NULL   OR "lanes:bus:forward" is not NULL OR "lanes:psv" is not NULL   OR "lanes:psv:forward" is not NULL   OR "maxheight:physical" is not NULL   OR "oneway:bus" is not NULL   OR "oneway:psv" is not NULL   OR "trolley_wire" is not NULL   OR "trolleybus" is not NULL   OR "tourist_bus:lanes" is not NULL   OR "psv" is not NULL   OR "psv:lanes" is not NULL   OR "highway" is 'busway'   OR "psv:lanes:forward" is not NULL OR "psv:lanes:backward" is not NULL'
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
    expression2 = QgsExpression('if("maxspeed" is not NULL, "maxspeed",  if("highway" = \'residential\',\'68\', if("highway" = \'motorway\',\'207\', if("highway" = \'motorway_link\',\'131\', if("highway" = \'tertiary\',\'96\', if("highway" = \'unclassified\',\'88\', if("highway" = \'trunk_link\',\'156\', if("highway" = \'primary\',\'114\', if("highway" = \'secondary\',\'106\', if("highway" = \'service\',\'55\', if("highway" = \'primary_link\',\'106\', if("highway" = \'trunk\',\'215\', if("highway" = \'tertiary_link\',\'98\', if("highway" = \'secondary_link\',\'100\', if("highway" = \'living_street\',\'40\',\'70\')))))))))))))))')

    context = QgsExpressionContext()
    context.appendScopes(QgsExpressionContextUtils.globalProjectLayerScopes(bus_lanes_layer))

    with edit(bus_lanes_layer):
        for f in bus_lanes_layer.getFeatures():
            context.setFeature(f)
            f['oneway_routing'] = expression1.evaluate(context)
            f['maxspeed_routing'] = expression2.evaluate(context)
            bus_lanes_layer.updateFeature(f)
    bus_lanes_layer.commitChanges()

    return OSM_bus_lanes_gpkg, bus_lanes_name