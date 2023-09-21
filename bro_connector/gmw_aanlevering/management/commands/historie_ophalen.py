from __future__ import print_function
from __future__ import unicode_literals
from __future__ import absolute_import
from __future__ import division

from django.core.management.base import BaseCommand

import pandas as pd
import pytz
import datetime
import reversion
import bro_uitgifte
import numpy as np


from gmw_aanlevering.models import (
    GroundwaterMonitoringWellStatic,
    GroundwaterMonitoringWellDynamic,
    GroundwaterMonitoringTubesStatic,
    GroundwaterMonitoringTubesDynamic,
    GeoOhmCable,
    ElectrodeStatic,
    ElectrodeDynamic,
    Event,
)


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("kvk_number", type=int)

    def handle(self, *args, **options):
        kvk_number = options["kvk_number"]

        bro_ids = bro_uitgifte.get_bro_ids(kvk_number)
        gmw_ids = bro_uitgifte.get_gmw_ids(bro_ids)

        print(str(len(gmw_ids)) + " bro ids found for organisation.")

        for well in GroundwaterMonitoringWellStatic.objects.all():
            if well.bro_id in gmw_ids:
                gmw_ids.remove(well.bro_id)

        print(str(len(gmw_ids)) + " not in database.")

        # Import the well data
        for id in range(len(gmw_ids)):
            gmw_element = bro_uitgifte.get_gmw_data(gmw_ids[id], True)
            gmw_dict, number_of_events, number_of_tubes = bro_uitgifte.make_dict(
                gmw_element
            )

            # Invullen initiële waarden.
            gmws = GroundwaterMonitoringWellStatic.objects.create(
                bro_id=gmw_dict.get("broId", None),
                construction_standard=gmw_dict.get("constructionStandard", None),
                coordinates=(
                    "POINT(" + gmw_dict.get("pos", None) + ")"
                ),  # -> Has a delivered location and a standardized location, which do we want? Used std for now
                delivery_accountable_party=gmw_dict.get(
                    "deliveryAccountableParty", None
                ),
                delivery_context=gmw_dict.get("deliveryContext", None),
                delivery_responsible_party=gmw_dict.get(
                    "deliveryResponsibleParty", None
                ),  # Not in XML ??? -> Same as delivery or is it our id or Zeeland ???
                horizontal_positioning_method=gmw_dict.get(
                    "horizontalPositioningMethod", None
                ),
                initial_function=gmw_dict.get("initialFunction", None),
                local_vertical_reference_point=gmw_dict.get(
                    "localVerticalReferencePoint", None
                ),
                monitoring_pdok_id=gmw_dict.get(
                    "monitoringPdokId", None
                ),  # Cannot find in XML
                nitg_code=gmw_dict.get("nitgCode", None),
                well_offset=gmw_dict.get("offset", None),
                olga_code=gmw_dict.get("olgaCode", None),  # -> Cannot find in XML
                quality_regime=gmw_dict.get("qualityRegime", None),
                reference_system=gmw_dict.get(
                    "referenceSystem", None
                ),  # -> Cannot find in XML, but the reference vertical is NAP?
                registration_object_type=gmw_dict.get(
                    "registrationStatus", None
                ),  # -> registration status? Otherwise cannot find.
                request_reference=gmw_dict.get("requestReference", None),
                under_privilege=gmw_dict.get(
                    "underReview", None
                ),  # -> Not in XML, maybe under review?
                vertical_datum=gmw_dict.get("verticalDatum", None),
                well_code=gmw_dict.get("wellCode", None),
                ## Have to readjust the methodology slightly because if there are multiple events they cannot all have the same names and dates...
            )  # -> Is soms ook niet gedaan, dus nvt? Maar moet datum opgeven...)
            gmws.save()

            gmwd = GroundwaterMonitoringWellDynamic.objects.create(
                groundwater_monitoring_well=gmws,
                deliver_gld_to_bro=gmw_dict.get(
                    "deliverGldToBro", False
                ),  # std True because we are collecting data from BRO
                ground_level_position=gmw_dict.get("groundLevelPosition", None),
                ground_level_positioning_method=gmw_dict.get(
                    "groundLevelPositioningMethod", None
                ),
                ground_level_stable=gmw_dict.get("groundLevelStable", None),
                maintenance_responsible_party=gmw_dict.get(
                    "maintenanceResponsibleParty", None
                ),  # not in XML
                number_of_standpipes=gmw_dict.get(
                    "numberOfStandpipes", None
                ),  # not in XML
                owner=gmw_dict.get("owner", None),
                well_head_protector=gmw_dict.get("wellHeadProtector", None),
                well_stability=gmw_dict.get("wellStability", None),
            )  # not in XML)
            gmwd.save()

            try:
                for tube_number in range(number_of_tubes):
                    tube_number = tube_number + 1
                    prefix = "tube_" + str(tube_number) + "_"
                    gmts = GroundwaterMonitoringTubesStatic.objects.create(
                        groundwater_monitoring_well=gmws,
                        artesian_well_cap_present=gmw_dict.get(
                            prefix + "artesianWellCapPresent", None
                        ),
                        deliver_gld_to_bro=gmw_dict.get(
                            prefix + "deliverGldToBro", False
                        ),  # std True because we are collecting data from BRO
                        number_of_geo_ohm_cables=gmw_dict.get(
                            prefix + "numberOfGeoOhmCables", None
                        ),
                        screen_length=gmw_dict.get(
                            prefix + "screenLength", None
                        ),
                        sediment_sump_length=gmw_dict.get(
                            prefix + "sedimentSumpLength", None
                        ),  # not in XML --> might be because sediment sump not present, if else statement.
                        sediment_sump_present=gmw_dict.get(
                            prefix + "sedimentSumpPresent", None
                        ),
                        sock_material=gmw_dict.get(
                            prefix + "sockMaterial", None
                        ),
                        tube_material=gmw_dict.get(
                            prefix + "tubeMaterial", None
                        ),
                        tube_number=gmw_dict.get(prefix + "tubeNumber", None),
                        tube_type=gmw_dict.get(prefix + "tubeType", None),
                    )
                    gmts.save()

                    gmtd = GroundwaterMonitoringTubesDynamic.objects.create(
                        groundwater_monitoring_tube_static=gmts,
                        glue=gmw_dict.get(prefix + "glue", None),
                        inserted_part_diameter=gmw_dict.get(
                            prefix + "insertedPartDiameter", None
                        ),
                        inserted_part_length=gmw_dict.get(
                            prefix + "insertedPartLength", None
                        ),
                        inserted_part_material=gmw_dict.get(
                            prefix + "insertedPartMaterial", None
                        ),
                        plain_tube_part_length=gmw_dict.get(
                            prefix + "plainTubePartLength", None
                        ),
                        tube_packing_material=gmw_dict.get(
                            prefix + "tubePackingMaterial", None
                        ),
                        tube_status=gmw_dict.get(prefix + "tubeStatus", None),
                        tube_top_diameter=gmw_dict.get(
                            prefix + "tubeTopDiameter", None
                        ),
                        tube_top_position=gmw_dict.get(
                            prefix + "tubeTopPosition", None
                        ),
                        tube_top_positioning_method=gmw_dict.get(
                            prefix + "tubeTopPositioningMethod", None
                        ),
                        variable_diameter=gmw_dict.get(
                            prefix + "variableDiameter", None
                        ),
                    )
                    gmtd.save()

                    try:
                        if int(gmts.number_of_geo_ohm_cables) == 1:
                            geoc = GeoOhmCable.objects.create(
                                groundwater_monitoring_tube_static=gmts,
                                cable_number=gmw_dict.get(prefix + "cableNumber", None),
                            )  # not in XML -> 0 cables)
                            geoc.save()

                            eles = ElectrodeStatic.objects.create(
                                geo_ohm_cable=geoc,
                                electrode_packing_material=gmw_dict.get(
                                    prefix + "electrodePackingMaterial", None
                                ),
                                electrode_position=gmw_dict.get(
                                    prefix + "electrodePosition", None
                                ),
                            )
                            eles.save()

                            eled = ElectrodeDynamic.objects.create(
                                electrode_static=eles,
                                electrode_number=gmw_dict.get(
                                    prefix + "electrodeNumber", None
                                ),
                                electrode_status=gmw_dict.get(
                                    prefix + "electrodeStatus", None
                                ),
                            )
                            eled.save()
                        elif int(gmts.number_of_geo_ohm_cables) > 1:
                            print(gmw_dict)
                            exit(print("Multiple Ohm Cables found for the first time. Adjust script. Message steven.hosper@nelen-schuurmans.nl"))
                    except:
                        pass
            except:
                pass

            event = Event.objects.create(
                event_name = "construction",
                event_date = bro_uitgifte.get_mytimezone_date(gmw_dict.get(
                    "construction_date", None
                )),
                groundwater_monitoring_well_static = gmws,
                groundwater_monitoring_well_dynamic = gmwd,
            )

            event.save()

            # Update based on the events
            for nr in range(number_of_events):
                nr = nr + 1
                prefix = "event_" + str(nr) + "_"
                event_updates = bro_uitgifte.slice(gmw_dict, prefix)

                try:
                    event = Event.objects.create(
                        event_name = event_updates['eventName'],
                        event_date = bro_uitgifte.get_mytimezone_date(event_updates['date']),
                    )
                except:
                    try:
                        event = Event.objects.create(
                            event_name = event_updates['eventName'],
                            event_date = bro_uitgifte.get_mytimezone_date(str(event_updates['year']) + "-01-01"),
                        )
                    except:
                        print(event_updates)
                        exit()
                
                # Check for well data
                if event_updates.get('wellData', True):
                    # Check for tube data
                    if event_updates.get('tubeData', True):
                        # Check for electrode data
                        if event_updates.get('electrodeData', True):
                            print("Unknown data")
                            print(event_updates)
                        else:
                            # Clone row and make new primary key with save
                            new_eleds = ElectrodeDynamic.objects.filter(
                                electrode_static = eles)
                            
                            # This assumes the gmwds are sorted based on creation date.
                            if len(new_eleds) == 1:
                                new_eled = new_eleds.first()
                                new_eled.electrode_dynamic_id = None
                            
                            elif len(new_gmtds) > 1:
                                new_eled = new_gmtds.last()
                                new_eled.electrode_dynamic_id = None
                            
                            else:
                                raise Exception("No Groundwater Monitoring Tube Dynamic Tables found for this GMT: ", gmts)

                            # Check what has to be changed
                            new_eled = bro_uitgifte.update_electrode_dynamic(new_eled, event_updates)

                            # Save and add new key to event
                            new_eled.save()

                            # Add to the event.
                            event.electrode_dynamic = new_eled
                            event.groundwater_monitoring_well_static = gmws
                            event.save()

                    else:
                        # Find which filter needs to be adjusted
                        new_gmts = GroundwaterMonitoringTubesStatic.objects.get(
                            tube_number = event_updates['tubeNumber'],
                            groundwater_monitoring_well = gmws,
                            )

                        # Clone row and make new primary key with save
                        new_gmtds = GroundwaterMonitoringTubesDynamic.objects.filter(
                            groundwater_monitoring_tube_static = new_gmts)
                        
                        # This assumes the gmwds are sorted based on creation date.
                        if len(new_gmtds) == 1:
                            new_gmtd = new_gmtds.first()
                            new_gmtd.groundwater_monitoring_tube_dynamic_id = None
                        
                        elif len(new_gmtds) > 1:
                            new_gmtd = new_gmtds.last()
                            new_gmtd.groundwater_monitoring_tube_dynamic_id = None
                        
                        else:
                            raise Exception("No Groundwater Monitoring Tube Dynamic Tables found for this GMT: ", gmts)

                        # Check what has to be changed
                        new_gmtd = bro_uitgifte.update_tube_dynamic(new_gmtd, event_updates)


                        # Save and add new key to event
                        new_gmtd.save()
                        
                        #  Add to the event
                        event.groundwater_monitoring_well_static = gmws
                        event.groundwater_monitoring_well_tube_dynamic = new_gmtd
                        event.save()
                else:
                    # Clone row and make new primary key with save
                    new_gmwds = GroundwaterMonitoringWellDynamic.objects.filter(
                        groundwater_monitoring_well = gmws)
                    
                    # This assumes the gmwds are sorted based on creation date.
                    if len(new_gmwds) == 1:
                        new_gmwd = new_gmwds.first()
                        new_gmwd.groundwater_monitoring_well_dynamic_id = None
                    
                    elif len(new_gmwds) > 1:
                        new_gmwd = new_gmwds.last()
                        new_gmwd.groundwater_monitoring_well_dynamic_id = None
                    
                    else:
                        raise Exception("No Groundwater Monitoring Well Dynamic Tables found for this GMW: ", gmws)

                    
                    # Check what has to be changed
                    new_gmwd = bro_uitgifte.update_well_dynamic(new_gmwd, event_updates)


                    # Save and add new key to event
                    new_gmwd.save()
                    
                    # Add to the event.
                    event.groundwater_monitoring_well_static = gmws
                    event.groundwater_monitoring_well_dynamic = new_gmwd
                    event.save()
                

            if gmw_dict.get("removal_date", None) is not None:
                event = Event.objects.create(
                    event_name = "removal",
                    event_date = bro_uitgifte.get_mytimezone_date(gmw_dict.get(
                        "removal_date", None
                    )),
                    groundwater_monitoring_well_static = gmws,
                    groundwater_monitoring_well_dynamic = gmwd,
                )
                event.save()

            if id % 25 == 0:
                print(round(id / len(gmw_ids), 2) * 100, "% Complete")

            
