# Global Metropolitan Area to Commercial Airport Mapping (Large & Medium Hubs Only)
# Key format: (city_name_lower, iso_country) -> [IATA codes]
# iso_country uses 2-letter ISO 3166-1 alpha-2 codes (e.g. "US", "GB", "JP")
# This mapping focuses on primary and secondary airports with scheduled passenger services.

CITY_AIRPORT_MAP = {
    # --- North America ---
    ("new york", "US"):         ["JFK", "EWR", "LGA", "HPN", "SWF"],
    ("los angeles", "US"):      ["LAX", "BUR", "SNA", "ONT", "LGB"],
    ("san francisco", "US"):    ["SFO", "OAK", "SJC"],
    ("chicago", "US"):          ["ORD", "MDW"],
    ("washington d.c.", "US"):  ["IAD", "DCA", "BWI"],
    ("miami", "US"):            ["MIA", "FLL", "PBI"],
    ("dallas", "US"):           ["DFW", "DAL"],
    ("houston", "US"):          ["IAH", "HOU"],
    ("toronto", "CA"):          ["YYZ", "YTZ", "YHM"],

    # --- Europe ---
    ("london", "GB"):           ["LHR", "LGW", "STN", "LTN", "LCY", "SEN"],
    ("paris", "FR"):            ["CDG", "ORY", "BVA"],
    ("berlin", "DE"):           ["BER"],
    ("frankfurt", "DE"):        ["FRA", "HHN"],
    ("milan", "IT"):            ["MXP", "LIN", "BGY"],
    ("rome", "IT"):             ["FCO", "CIA"],
    ("moscow", "RU"):           ["SVO", "DME", "VKO", "ZIA"],
    ("istanbul", "TR"):         ["IST", "SAW"],
    ("stockholm", "SE"):        ["ARN", "BMA", "NYO", "VST"],
    ("brussels", "BE"):         ["BRU", "CRL"],

    # --- Asia ---
    ("tokyo", "JP"):            ["HND", "NRT"],
    ("osaka", "JP"):            ["KIX", "ITM", "UKB"],
    ("seoul", "KR"):            ["ICN", "GMP"],
    ("beijing", "CN"):          ["PEK", "PKX"],
    ("shanghai", "CN"):         ["PVG", "SHA"],
    ("chengdu", "CN"):          ["CTU", "TFU"],
    ("bangkok", "TH"):          ["BKK", "DMK"],
    ("taipei", "TW"):           ["TPE", "TSA"],
    ("kuala lumpur", "MY"):     ["KUL", "SZB"],
    ("jakarta", "ID"):          ["CGK", "HLP"],
    ("dubai", "AE"):            ["DXB", "DWC"],

    # --- Others ---
    ("sydney", "AU"):           ["SYD"],
    ("melbourne", "AU"):        ["MEL", "AVV"],
    ("sao paulo", "BR"):        ["GRU", "CGH", "VCP"],
    ("rio de janeiro", "BR"):   ["GIG", "SDU"],
    ("johannesburg", "ZA"):     ["JNB", "HLA"],
}
