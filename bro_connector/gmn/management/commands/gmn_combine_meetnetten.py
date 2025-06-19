import re
from collections import defaultdict
from django.db import models
from django.db.models.query import QuerySet
from django.core.management.base import BaseCommand
from gmn.models import GroundwaterMonitoringNet, MeasuringPoint, Subgroup
from gmw.models import GroundwaterMonitoringTubeStatic
import numpy as np
from datetime import datetime, timedelta, tzinfo

class Command(BaseCommand):
    """This command handles all 4 type of registrations for GMN's
    It uses the IntermediateEvents table as input.
    In this table, the event_type column holds the information for which BRO request to handle.
    The synced_to_bro column is the administration for whether the information is allready sent to the BRO.
    The deliver_to_bro in the event determines whether a event should be synced.

    The 4 requests that are handled are:
        - GMN_StartRegistration
        - GMN_MeasuringPoint
        - GMN_MeasuringPointEndDate
        - GMN_Closure


    GMNs:
    - krw_kwal_{year}
    - GAR_{year}
    - krw_kantiteit{year}
    - kmg_kwal_{year}
    - PMG_kwantiteit_{extra}

    """
    def add_arguments(self, parser):
        parser.add_argument(
            "--delete",
            type=str,
            choices=["Yes", "No"],
            help="Verwijder existing base nets.",
        )

    def handle(self, *args, **options):
        delete = True if options["delete"] == "Yes" else False
        gmn_grouped = group_monitoring_nets()
        for group, gmn_data in gmn_grouped.items():
            if delete:
                gmn_data = delete_base(group, gmn_data)
            gmn = create_monitoring_net(group, gmn_data)
            update_monitoring_net(gmn, gmn_data)
            # if delete:
            #     remove_monitoring_nets(gmn, gmn_data)

def delete_base(group, gmn_data):
    base = GroundwaterMonitoringNet.objects.filter(name=group).all()
    if base:
        for gmn in base:
            gmn.delete()

    gmn_data_filtered = [item for item in gmn_data if item[1] != group]       

    return gmn_data_filtered
    
def group_monitoring_nets():
    gmn_names = GroundwaterMonitoringNet.objects.all().values_list('name', flat=True)
    gmn_ids = GroundwaterMonitoringNet.objects.all().values_list('id', flat=True)
    pattern = re.compile(r'^(.*?)[_]?(\d{4}|extra)$')

    # Step 1: Identify all prefix-suffix pairs
    grouped = defaultdict(list)
    suffix_type = {}

    for name,id in zip(gmn_names,gmn_ids):
        match = pattern.fullmatch(name)
        if match:
            prefix, suffix = match.group(1), match.group(2)
            grouped[prefix].append((suffix, id, name))
            suffix_type[suffix] = "year" if suffix.isdigit() else "extra"
    # Step 2: Identify "bare" prefix entries (no suffix)
    for id, name in zip(gmn_ids,gmn_names):
        if name in grouped.keys():
            grouped[name].append(("0", id, name))  # Assign suffix '0' to treat as oldest

    # Step 3: Sort each group's items: bare < years < extra
    ## If monitoring_nets have the same name, take the one that is created first as oldest
    def sort_key(item):
        suffix, _, _ = item
        if suffix == "0":
            return (0, "")
        if suffix.isdigit():
            return (1, int(suffix))
        if suffix == "extra":
            return (2, "")
        return (3, suffix)  # fallback for unknown

    # Step 4: Output --> check sorting
    for prefix in grouped:
        group_sorted = sorted(grouped[prefix], key=sort_key)
        grouped[prefix] = [(val[1], val[2]) for val in group_sorted]

    return grouped

def create_monitoring_net(group, gmn_data):
    gmn_ids = [data[0] for data in gmn_data]

    base = GroundwaterMonitoringNet.objects.filter(name=group).first()
    if base: 
        field_names = [
            f.name for f in base.__class__._meta.get_fields()
            if isinstance(f, models.Field) and not f.auto_created and not f.primary_key
        ]
        field_values = {
            field: getattr(base, field)
            for field in field_names
        }
        field_values.update(gmn_bro_id=None)
        gmn = GroundwaterMonitoringNet.objects.create(**field_values)
        measuring_points = MeasuringPoint.objects.filter(gmn=base).all()
    else:
        oldest = GroundwaterMonitoringNet.objects.filter(id=gmn_ids[0]).first()
        field_names = [
            f.name for f in oldest.__class__._meta.get_fields()
            if isinstance(f, models.Field) and not f.auto_created and not f.primary_key
        ]
        field_values = {
            field: getattr(oldest, field)
            for field in field_names
        }
        field_values.update(name=group, gmn_bro_id=None)
        gmn = GroundwaterMonitoringNet.objects.create(**field_values)
        measuring_points = MeasuringPoint.objects.filter(gmn=oldest).all()

    return gmn

def update_monitoring_net(gmn: GroundwaterMonitoringNet, gmn_data):
    gmn_ids = [data[0] for data in gmn_data]
    gmn_names = [data[1] for data in gmn_data]

    for i, (gmn_id, gmn_name) in enumerate(zip(gmn_ids,gmn_names)):
        next_gmn = GroundwaterMonitoringNet.objects.get(id=gmn_id)
        addition, removal = update_measuring_points(gmn, next_gmn)
        if addition:
            print("Added measuring points to GMN")
        if removal: 
            print("Removed measuring points to GMN")

def update_measuring_points(gmn: GroundwaterMonitoringNet, next_gmn: GroundwaterMonitoringNet):

    def case_measuring_point_needs_to_be_added(measuring_points: QuerySet[MeasuringPoint], next_measuring_points: QuerySet[MeasuringPoint]):
        measuring_point_codes = list(set([m.code for m in measuring_points]))
        next_measuring_point_codes = list(set([m.code for m in next_measuring_points]))
        check = any([code not in measuring_point_codes for code in next_measuring_point_codes])

        if check:
            for measuring_point in next_measuring_points:
                if measuring_point.code not in measuring_point_codes:
                    measuring_point.gmn = gmn
                    measuring_point.added_to_gmn_date = next_gmn.start_date_monitoring
                    measuring_point.save()
                    print(measuring_point.added_to_gmn_date)
                    print("Added and saved")

        return check
    
    def case_measuring_point_needs_to_be_removed(measuring_points: QuerySet[MeasuringPoint], next_measuring_points: QuerySet[MeasuringPoint]):
        measuring_point_codes = list(set([m.code for m in measuring_points]))
        next_measuring_point_codes = list(set([m.code for m in next_measuring_points]))
        check = any([code not in next_measuring_point_codes for code in measuring_point_codes])

        if check:
            for measuring_point in measuring_points:
                if measuring_point.code not in next_measuring_point_codes and not measuring_point.deleted_from_gmn_date:
                    measuring_point.deleted_from_gmn_date = next_gmn.start_date_monitoring - timedelta(days=1)
                    measuring_point.save()
        
        return check
    
    measuring_points = MeasuringPoint.objects.filter(gmn=gmn).all()
    next_measuring_points = MeasuringPoint.objects.filter(gmn=next_gmn).all()
    
    addition_check = case_measuring_point_needs_to_be_added(measuring_points, next_measuring_points)
    removal_check = case_measuring_point_needs_to_be_removed(measuring_points, next_measuring_points)

    return addition_check, removal_check
    