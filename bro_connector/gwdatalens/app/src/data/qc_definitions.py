"""The definitions for the quality control flags and rules."""

qc_categories = {
    "QC0i": "Verstopt filter",
    "QC0j": "Ijsvorming in buis",
    "QC2b": "Tijdsverschuiving",
    "QC2c": "Afwijking meetbereik",
    "QC2d": "Temperatuurafwijking",
    "QC2e": "Hysteresis",
    "QC2g": "Hapering sensor",
    "QC2h": "Falen sensor",
    "QC2i": "Sterke ruis",
    "QC2j": "Falen instrument",
    "QC3a": "Droogval buis",
    "QC3b": "Droogval filter",
    "QC3c": "Droogval sensor",
    "QC3d": "Vollopen buis",
    "QC3e": "Overlopen buis",
    "QC3g": "Onderschreiding minimum",
    "QC3h": "Overschreiding maximum	",
    "QC4a": "Onwaarschijnlijke waarde",
    "QC4b": "Filterverwisseling",
    "QC4c": "Onwaarschijnlijke sprong ",
    "QC4d": "Onvoldoende variatie",
    "QC4e": "Onvoldoende samenhang",
    "QC5a": "Betrouwbaarheid",
    "QC5b": "Nauwkeurigheid",
}

rule_explanation_en = {
    "rule_funcdict_to_nan": (
        "Detection rule, flag values with dictionary of functions"
    ),
    "rule_max_gradient": ("Detection rule, flag values when maximum gradient exceeded"),
    "rule_hardmax": ("Detection rule, flag values greater than threshold value"),
    "rule_hardmin": ("Detection rule, flag values lower than threshold value"),
    "rule_ufunc_threshold": (
        "Detection rule, flag values based on operator and threshold value"
    ),
    "rule_diff_ufunc_threshold": (
        "Detection rule, flag values based on diff, operator and threshold"
    ),
    "rule_other_ufunc_threshold": (
        "Detection rule, flag values based on other series and threshold."
    ),
    "rule_spike_detection": (
        "Detection rule, identify spikes in timeseries and set to NaN"
    ),
    "rule_offset_detection": ("Detection rule, detect periods with an offset error"),
    "rule_outside_n_sigma": (
        "Detection rule, set values outside of n * standard deviation to NaN"
    ),
    "rule_diff_outside_of_n_sigma": (
        "Detection rule, calculate diff of series and identify suspect"
    ),
    "rule_outside_bandwidth": (
        "Detection rule, set suspect values to NaN if outside bandwidth"
    ),
    "rule_pastas_outside_pi": (
        "Detection rule, flag values based on pastas model prediction interval"
    ),
    "rule_pastas_percentile_pi": (""),
    "rule_keep_comments": (
        "Filter rule, modify timeseries to keep data with certain comments"
    ),
    "rule_shift_to_manual_obs": (
        "Adjustment rule, for shifting timeseries onto manual observations"
    ),
    "rule_combine_nan_or": (
        "Combination rule, combine NaN values for any number of timeseries"
    ),
    "rule_combine_nan_and": (
        "Combination rule, combine NaN values for any number of timeseries"
    ),
    "rule_flat_signal": (
        "Detection rule, flag values based on dead signal in rolling window"
    ),
    "rule_compare_to_manual_obs": (
        "Detection rule, flag values based on comparison to manual observations"
    ),
}

rule_explanation_nl = {
    "rule_funcdict_to_nan": (
        "Detectie-regel, signaleer met behulp van een dictionary van functies"
    ),
    "rule_max_gradient": (
        "Detectie-regel, signaleer een te grote stijging in een bepaalde periode"
    ),
    "rule_hardmax": ("Detectie-regel, signaleer waarden hoger dan een drempelwaarde"),
    "rule_hardmin": ("Detectie-regel, signaleer waarden lager dan drempelwaarde"),
    "rule_ufunc_threshold": (
        "Detectie-regel, signaleer op basis van operator en drempelwaarde"
    ),
    "rule_diff_ufunc_threshold": (
        "Detectie-regel, signaleer op basss van verschil, operator en drempelwaarde"
    ),
    "rule_other_ufunc_threshold": (
        "Detectie-regel, signaleer op basis van andere reeks en toegestaan verschil"
    ),
    "rule_spike_detection": ("Detectie-regel, signaleer pieken"),
    "rule_offset_detection": (
        "Detectie-regel, signaleer perioden met een verschilfout"
    ),
    "rule_outside_n_sigma": ("Detectie-regel, signaleer buiten n * standaarddeviatie"),
    "rule_diff_outside_of_n_sigma": (
        "Detectie-regel, signaleer op basis van verandering in periode"
    ),
    "rule_outside_bandwidth": ("Detectie-regel, signaleer buiten de bandbreedte"),
    "rule_pastas_outside_pi": (
        "Detectie-regel, signaleer op basis van het voorspellingsinterval "
        "van een pastas model"
    ),
    "rule_pastas_percentile_pi": (""),
    "rule_keep_comments": (
        "Filter rule, pas reeks aan in waardeb met bepaalde opmerkingen te behouden"
    ),
    "rule_shift_to_manual_obs": (
        "Aanpassing-regel, pas waarden aan op basis van handmatige metingen"
    ),
    "rule_combine_nan_or": (
        "Combinatie-regel, signaleer waar één van de regels is geactiveerd"
    ),
    "rule_combine_nan_and": (
        "Combinatie-regel, signaleer waar alle regels zijn geactiveerd"
    ),
    "rule_flat_signal": ("Detectie-regel, signaleer op basis van een vlak signaal"),
    "rule_compare_to_manual_obs": (
        "Detectie regel, signaleer op basis van vergelijking met handmatige "
        "controle metingen"
    ),
}
