
<img src=../static/img/broconnector.png width="140">

# Klassendiagram voor Formatieweerstand Dossiers (FRD) #
```mermaid
classDiagram
    class Organisation{
        str name
        int company_number
        str color
        int bro_user
        int bro_token
    }
    class GroundwaterMonitoringTubeStatic{
        int groundwater_monitoring_tube_static_id
        GroundwaterMonitoringWellStatic groundwater_monitoring_well_static
        bool deliver_gld_to_bro
        int tube_number
        str tube_type
        str artesian_well_cap_present
        str sediment_sump_present
        str tube_material
        float screen_length
        str sock_material
        float sediment_sump_length
    }
    class GroundwaterMonitoringNet{
        int id
        BROProject project
        bool deliver_to_bro
        str gmn_bro_id
        Organisation delivery_accountable_party
        organisation delivery_responsible_party
        str quality_regime
        str object_id_accountable_party
        str name
        str delivery_context
        str monitoring_purpose
        str groundwater_aspect
        date start_date_monitoring
        date end_date_monitoring
        bool removed_from_BRO
        str description
        }


    class FormationResistanceDossier{
        str frd_bro_id
        Organisation delivery_accountable_party
        Organisation delivery_responsible_party
        str quality_regime
        str assessment_type
        GroundwaterMonitoringTubeStatic groundwater_monitoring_tube
        GroundwaterMonitoringNet groundwater_monitoring_net
        bool deliver_to_bro
        date closure_date
        bool closed_in_bro
        }
    FormationResistanceDossier ..> "del. acc. party, del. resp. party" Organisation
    FormationResistanceDossier ..> "groundwater_monitoring_tube" GroundwaterMonitoringTubeStatic
    FormationResistanceDossier ..> "groundwater_monitoring_net" GroundwaterMonitoringNet

    class ElectromagneticMeasurementMethod{
        FormationResistanceDossier formation_resistance_dossier
        date measurement_date
        Organisation measuring_responsible_party
        str measuring_procedure
        str assessment_procedure
    }
    ElectromagneticMeasurementMethod ..> "formation_resistance_dossier" FormationResistanceDossier

    class InstrumentConfiguration{
        FormationResistanceDossier formation_resistance_dossier
        str configuration_name
        ElectromagneticMeasurementMethod electromagnetic_measurement_method
        float relative_position_send_coil
        float relative_position_receive_coil
        str secondary_receive_coil
        float relative_position_secondary_coil
        str coilfrequency_known
        float coilfrequency
        float instrument_length
    }
    InstrumentConfiguration ..> "formation_resistance_dossier" FormationResistanceDossier
    InstrumentConfiguration ..> "electromagnetic_measurement_method" ElectromagneticMeasurementMethod

    class GeoOhmMeasurementMethod{
        FormationResistanceDossier formation_resistance_dossier
        date measurement_date
        Organisation measuring_responsible_party
        str measuring_procedure
        str assessment_procedure
    }
    GeoOhmMeasurementMethod ..> "formation_resistance_dossier" FormationResistanceDossier
    GeoOhmMeasurementMethod ..> "measuring_responsible_party" Organisation

    class GMWElectrodeReference{
        int cable_number
        int electrode_number
    }
    class ElectrodePair{
        GMWElectrodeReference elektrode1
        GMWElectrodeReference elektrode2
    }
    ElectrodePair ..> "elektrode1, elektrode2" GMWElectrodeReference

    class MeasurementConfiguration{
        FormationResistanceDossier formation_resistance_dossier
        str configuration_name
        ElectrodePair measurement_pair
        ElectrodePair flowcurrent_pair
    }
    MeasurementConfiguration ..> "formation_resistance_dossier" FormationResistanceDossier
    MeasurementConfiguration ..> "measurement_pair, flowcurrent_pair" ElectrodePair

    class ElectromagneticSeries{
        ElectromagneticMeasurementMethod electromagnetic_measurement_method
    }
    ElectromagneticSeries ..> "electromagnetic_measurement_method" ElectromagneticMeasurementMethod

    class GeoOhmMeasurementValue{
        GeoOhmMeasurementMethod geo_ohm_measurement_method
        float formationresistance
        MeasurementConfiguration measurement_configuration
        datetime datetime
    }
    GeoOhmMeasurementValue ..> "geo_ohm_measurement_method" GeoOhmMeasurementMethod
    GeoOhmMeasurementValue ..> "measurement_configuration" MeasurementConfiguration

    class ElectromagneticRecord{
        ElectromagneticSeries series
        float vertical_position
        float primary_measurement
        float secondary_measurement
    }
    ElectromagneticRecord ..> "series" ElectromagneticSeries

    class CalculatedFormationresistanceMethod{
        GeoOhmMeasurementMethod geo_ohm_measurement_method
        ElectromagneticMeasurementMethod electromagnetic_measurement_method
        str responsible_party
        str assessment_procedure
    }
    CalculatedFormationresistanceMethod ..> "geo_ohm_measurement_method"  GeoOhmMeasurementMethod
    CalculatedFormationresistanceMethod ..> "electromagnetic_measurement_method" ElectromagneticMeasurementMethod

    class FormationresistanceSeries{
        CalculatedFormationresistanceMethod calculated_formationresistance
    }
    FormationresistanceSeries ..> "calculated_formationresistance" CalculatedFormationresistanceMethod

    class FormationresistanceRecord{
        FormationresistanceSeries series
        float vertical_position
        float formationresistance
        str status_qualitycontrol
    }
    FormationresistanceRecord ..> "series" FormationresistanceSeries

    class FrdSyncLog{
        bool synced
        datetime date_modified
        str bro_id
        str event_type
        FormationResistanceDossier frd
        GeoOhmMeasurementMethod geo_ohm_measuring_method
        ElectromagneticMeasurementMethod electomagnetic_method
        str process_status
        str comment
        str xml_filepath
        int delivery_status
        str delivery_status_info
        str delivery_id
        str delivery_type
    }
    FrdSyncLog ..> "frd" FormationResistanceDossier
    FrdSyncLog ..> "geo_ohm_measuring_method" GeoOhmMeasurementMethod
    FrdSyncLog ..> "electomagnetic_method" GeoOElectromagneticMeasurementMethodhmMeasurementMethod

```

# FRD - Formatieweerstand Dossiers 

Binnen deze groep vallen de dossiers, en alle benodigde objecten voor de samenstelling hiervan, die gaan over zoutwachter metingen.
Hieronder 


## Organisaties

Uitleg over de werking van Organisaties....


## Projecten

Uitleg over de werking van Projecten....