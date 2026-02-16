from classes.s3_buckets import S3Bucket
from anthropic import AsyncAnthropic, RateLimitError
from dotenv import load_dotenv
import os, logging, json, asyncio, time
from pydantic import BaseModel, Field

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

dict_of_sections_and_pages = {
    "run_time": "0:01:11.880744",
    "section_page_index": {
        "00": {
            "000002": {
                "multi": [
                    [
                        2,
                        3,
                        4,
                        5,
                        6,
                        7
                    ]
                ],
                "single": [],
                "title": "Undocumented Section Number (MSF2020)"
            },
            "000003": {
                "multi": [],
                "single": [
                    2
                ],
                "title": "Undocumented Section Number (MSF2020)"
            },
            "003132": {
                "multi": [],
                "single": [
                    2,
                    8
                ],
                "title": "Geotechnical Data"
            },
            "003132a": {
                "multi": [],
                "single": [
                    2
                ],
                "title": "Undocumented Section Number (MSF2020)"
            },
            "003132b": {
                "multi": [],
                "single": [
                    2
                ],
                "title": "Undocumented Section Number (MSF2020)"
            }
        },
        "01": {
            "012200": {
                "multi": [],
                "single": [
                    2,
                    64
                ],
                "title": "Unit Prices"
            },
            "012300": {
                "multi": [
                    [
                        65,
                        66
                    ]
                ],
                "single": [
                    2
                ],
                "title": "Alternates"
            },
            "012500": {
                "multi": [
                    [
                        67,
                        68,
                        69,
                        70
                    ]
                ],
                "single": [
                    2,
                    115,
                    118,
                    1062,
                    1319
                ],
                "title": "Substitution Procedures"
            },
            "012500a": {
                "multi": [],
                "single": [
                    2,
                    71
                ],
                "title": "Undocumented Section Number (MSF2020)"
            },
            "012500b": {
                "multi": [
                    [
                        72,
                        73
                    ]
                ],
                "single": [
                    2
                ],
                "title": "Undocumented Section Number (MSF2020)"
            },
            "012613.13": {
                "multi": [],
                "single": [
                    88
                ],
                "title": "Undocumented Section Number (MSF2020)"
            },
            "013000": {
                "multi": [],
                "single": [
                    227,
                    292,
                    394,
                    1040
                ],
                "title": "Administrative Requirements"
            },
            "013100": {
                "multi": [
                    [
                        74,
                        75,
                        76,
                        77,
                        78,
                        79,
                        80,
                        81,
                        82,
                        83,
                        84
                    ]
                ],
                "single": [
                    2,
                    100,
                    889
                ],
                "title": "Project Management and Coordination"
            },
            "013100a": {
                "multi": [],
                "single": [
                    2,
                    76
                ],
                "title": "Undocumented Section Number (MSF2020)"
            },
            "013100b": {
                "multi": [],
                "single": [
                    2
                ],
                "title": "Undocumented Section Number (MSF2020)"
            },
            "013113": {
                "multi": [
                    [
                        89,
                        90,
                        91,
                        92,
                        93,
                        94,
                        95,
                        96
                    ]
                ],
                "single": [
                    2,
                    103
                ],
                "title": "Project Coordination"
            },
            "013300": {
                "multi": [
                    [
                        97,
                        98,
                        99,
                        100,
                        101,
                        102,
                        103,
                        104,
                        105,
                        106,
                        107,
                        108
                    ]
                ],
                "single": [
                    2,
                    67,
                    115,
                    412
                ],
                "title": "Submittal Procedures"
            },
            "013300a": {
                "multi": [],
                "single": [
                    2,
                    101,
                    108
                ],
                "title": "Undocumented Section Number (MSF2020)"
            },
            "013300b": {
                "multi": [],
                "single": [
                    2,
                    109
                ],
                "title": "Undocumented Section Number (MSF2020)"
            },
            "013300c": {
                "multi": [],
                "single": [
                    2,
                    110
                ],
                "title": "Undocumented Section Number (MSF2020)"
            },
            "014000": {
                "multi": [],
                "single": [
                    113,
                    164,
                    207,
                    342,
                    974,
                    1156,
                    1221
                ],
                "title": "Quality Requirements"
            },
            "014339": {
                "multi": [
                    [
                        111,
                        112,
                        113,
                        114
                    ]
                ],
                "single": [
                    2
                ],
                "title": "Mockups"
            },
            "015000": {
                "multi": [],
                "single": [
                    125
                ],
                "title": "Temporary Facilities and Controls"
            },
            "016000": {
                "multi": [
                    [
                        115,
                        116,
                        117,
                        118,
                        119
                    ]
                ],
                "single": [
                    2,
                    228,
                    414,
                    642
                ],
                "title": "Product Requirements"
            },
            "017300": {
                "multi": [],
                "single": [
                    986
                ],
                "title": "Execution"
            },
            "017329": {
                "multi": [],
                "single": [
                    1181
                ],
                "title": "Cutting and Patching"
            },
            "017419": {
                "multi": [],
                "single": [
                    125,
                    468
                ],
                "title": "Construction Waste Management and Disposal"
            },
            "017700": {
                "multi": [
                    [
                        120,
                        121,
                        122,
                        123,
                        124,
                        125
                    ]
                ],
                "single": [
                    2,
                    117,
                    1110,
                    1315
                ],
                "title": "Closeout Procedures"
            },
            "017800": {
                "multi": [],
                "single": [
                    452
                ],
                "title": "Closeout Submittals"
            },
            "017823": {
                "multi": [],
                "single": [
                    1125,
                    1155,
                    1193
                ],
                "title": "Operation and Maintenance Data"
            },
            "017839": {
                "multi": [],
                "single": [
                    1017
                ],
                "title": "Project Record Documents"
            }
        },
        "03": {
            "033000": {
                "multi": [
                    [
                        126,
                        127,
                        128,
                        129,
                        130,
                        131,
                        132,
                        133,
                        134,
                        135,
                        136,
                        137,
                        138,
                        139,
                        140,
                        141,
                        142,
                        143,
                        144,
                        145,
                        146,
                        147,
                        148,
                        149,
                        150,
                        151,
                        152,
                        153,
                        154,
                        155,
                        156,
                        157,
                        158,
                        159
                    ],
                    [
                        1159,
                        1160
                    ]
                ],
                "single": [
                    2,
                    188,
                    411,
                    421,
                    944,
                    983,
                    989,
                    1088,
                    1168
                ],
                "title": "Cast-in-Place Concrete"
            }
        },
        "04": {
            "042000": {
                "multi": [
                    [
                        160,
                        161,
                        162,
                        163,
                        164
                    ]
                ],
                "single": [
                    2
                ],
                "title": "Unit Masonry"
            },
            "044313": {
                "multi": [
                    [
                        165,
                        166,
                        167,
                        168,
                        169,
                        170
                    ]
                ],
                "single": [
                    2
                ],
                "title": "Stone Masonry Veneer"
            },
            "047200": {
                "multi": [
                    [
                        171,
                        172,
                        173,
                        174,
                        175
                    ]
                ],
                "single": [
                    2
                ],
                "title": "Cast Stone Masonry"
            }
        },
        "05": {
            "051200": {
                "multi": [
                    [
                        176,
                        177,
                        178,
                        179,
                        180,
                        181,
                        182,
                        183,
                        184,
                        185,
                        186,
                        187,
                        188
                    ]
                ],
                "single": [
                    2
                ],
                "title": "Structural Steel Framing"
            },
            "051213": {
                "multi": [],
                "single": [
                    176
                ],
                "title": "Architecturally-Exposed Structural Steel Framing"
            },
            "053100": {
                "multi": [
                    [
                        188,
                        189,
                        190,
                        191,
                        192,
                        193,
                        194,
                        195
                    ]
                ],
                "single": [
                    2,
                    176
                ],
                "title": "Steel Decking"
            },
            "054000": {
                "multi": [
                    [
                        196,
                        197,
                        198,
                        199,
                        200,
                        201,
                        202,
                        203,
                        204,
                        205
                    ]
                ],
                "single": [
                    2,
                    246,
                    374
                ],
                "title": "Cold-Formed Metal Framing"
            },
            "055000": {
                "multi": [
                    [
                        206,
                        207,
                        208,
                        209,
                        210
                    ],
                    [
                        1223,
                        1224
                    ]
                ],
                "single": [
                    2,
                    176,
                    188,
                    436,
                    942,
                    944
                ],
                "title": "Metal Fabrications"
            }
        },
        "06": {
            "061000": {
                "multi": [
                    [
                        211,
                        212,
                        213,
                        214,
                        215,
                        216,
                        217,
                        218
                    ]
                ],
                "single": [
                    3,
                    261,
                    266,
                    338,
                    914
                ],
                "title": "Rough Carpentry"
            },
            "061000.01": {
                "multi": [],
                "single": [
                    98
                ],
                "title": "Undocumented Section Number (MSF2020)"
            },
            "061000.01A": {
                "multi": [],
                "single": [
                    98
                ],
                "title": "Undocumented Section Number (MSF2020)"
            },
            "061600": {
                "multi": [
                    [
                        219,
                        220,
                        221
                    ]
                ],
                "single": [
                    3
                ],
                "title": "Sheathing"
            }
        },
        "07": {
            "071113": {
                "multi": [],
                "single": [
                    992
                ],
                "title": "Bituminous Dampproofing"
            },
            "071300": {
                "multi": [
                    [
                        222,
                        223,
                        224,
                        225
                    ]
                ],
                "single": [
                    3
                ],
                "title": "Sheet Waterproofing"
            },
            "071353": {
                "multi": [],
                "single": [
                    992
                ],
                "title": "Elastomeric Sheet Waterproofing"
            },
            "072022": {
                "multi": [],
                "single": [
                    34
                ],
                "title": "Undocumented Section Number (MSF2020)"
            },
            "072100": {
                "multi": [
                    [
                        226,
                        227,
                        228,
                        229
                    ]
                ],
                "single": [
                    3,
                    222
                ],
                "title": "Thermal Insulation"
            },
            "072119": {
                "multi": [
                    [
                        230,
                        231,
                        232,
                        233,
                        234
                    ]
                ],
                "single": [
                    3
                ],
                "title": "Foamed-In-Place Insulation"
            },
            "072419": {
                "multi": [],
                "single": [
                    219
                ],
                "title": "Water-Drainage Exterior Insulation and Finish System"
            },
            "072714": {
                "multi": [
                    [
                        235,
                        236,
                        237,
                        238,
                        239,
                        240,
                        241,
                        242,
                        243,
                        244,
                        245
                    ]
                ],
                "single": [
                    3,
                    165,
                    226,
                    338
                ],
                "title": "Undocumented Section Number (MSF2020)"
            },
            "074213": {
                "multi": [
                    [
                        246,
                        247,
                        248,
                        249,
                        250,
                        251
                    ]
                ],
                "single": [
                    3,
                    323
                ],
                "title": "Metal Wall Panels"
            },
            "074215": {
                "multi": [
                    [
                        252,
                        253,
                        254,
                        255,
                        256,
                        257,
                        258,
                        259,
                        260
                    ]
                ],
                "single": [
                    3
                ],
                "title": "Undocumented Section Number (MSF2020)"
            },
            "075200": {
                "multi": [
                    [
                        261,
                        262,
                        263,
                        264,
                        265,
                        266,
                        267,
                        268,
                        269
                    ]
                ],
                "single": [
                    3,
                    66,
                    226
                ],
                "title": "Modified Bituminous Membrane Roofing"
            },
            "075323": {
                "multi": [
                    [
                        270,
                        271,
                        272,
                        273,
                        274,
                        275,
                        276,
                        277,
                        278,
                        279,
                        280
                    ]
                ],
                "single": [
                    3,
                    66
                ],
                "title": "Ethylene-Propylene-Diene-Monomer Roofing"
            },
            "076200": {
                "multi": [],
                "single": [
                    165
                ],
                "title": "Sheet Metal Flashing and Trim"
            },
            "077100": {
                "multi": [
                    [
                        281,
                        282,
                        283,
                        284,
                        285,
                        286,
                        287
                    ]
                ],
                "single": [
                    3
                ],
                "title": "Roof Specialties"
            },
            "077200": {
                "multi": [
                    [
                        288,
                        289,
                        290,
                        291
                    ]
                ],
                "single": [
                    3
                ],
                "title": "Roof Accessories"
            },
            "078100": {
                "multi": [
                    [
                        292,
                        293,
                        294,
                        295
                    ]
                ],
                "single": [
                    3
                ],
                "title": "Applied Fire Protection"
            },
            "078413": {
                "multi": [
                    [
                        296,
                        297,
                        298,
                        299,
                        300,
                        301,
                        302,
                        303
                    ],
                    [
                        1273,
                        1274
                    ]
                ],
                "single": [
                    3,
                    911,
                    923,
                    943,
                    957,
                    994,
                    1190,
                    1214,
                    1223,
                    1291,
                    1309
                ],
                "title": "Penetration Firestopping"
            },
            "079200": {
                "multi": [],
                "single": [
                    144,
                    160,
                    165,
                    169,
                    171,
                    246,
                    321,
                    330,
                    338,
                    341,
                    355,
                    370,
                    450,
                    996
                ],
                "title": "Joint Sealants"
            }
        },
        "08": {
            "081113": {
                "multi": [
                    [
                        304,
                        305,
                        306,
                        307,
                        308,
                        309,
                        310
                    ]
                ],
                "single": [
                    3,
                    313
                ],
                "title": "Hollow Metal Doors and Frames"
            },
            "081416": {
                "multi": [
                    [
                        310,
                        311,
                        312,
                        313
                    ]
                ],
                "single": [
                    3
                ],
                "title": "Flush Wood Doors"
            },
            "084113": {
                "multi": [
                    [
                        314,
                        315,
                        316,
                        317,
                        318,
                        319,
                        320,
                        321,
                        322,
                        323
                    ]
                ],
                "single": [
                    3,
                    327,
                    361
                ],
                "title": "Aluminum-Framed Entrances and Storefronts"
            },
            "084413": {
                "multi": [
                    [
                        323,
                        324,
                        325,
                        326,
                        327,
                        328,
                        329,
                        330
                    ]
                ],
                "single": [
                    3,
                    246,
                    284,
                    361
                ],
                "title": "Glazed Aluminum Curtain Walls"
            },
            "084433": {
                "multi": [
                    [
                        331,
                        332,
                        333,
                        334,
                        335,
                        336,
                        337
                    ]
                ],
                "single": [
                    3
                ],
                "title": "Sloped Glazing Assemblies"
            },
            "085113": {
                "multi": [
                    [
                        338,
                        339,
                        340,
                        341,
                        342,
                        343
                    ]
                ],
                "single": [
                    3
                ],
                "title": "Aluminum Windows"
            },
            "087100": {
                "multi": [
                    [
                        308,
                        309,
                        310
                    ]
                ],
                "single": [
                    3,
                    304,
                    313,
                    1312,
                    1332
                ],
                "title": "Door Hardware"
            },
            "087111": {
                "multi": [
                    [
                        344,
                        345,
                        346,
                        347,
                        348,
                        349,
                        350,
                        351,
                        352,
                        353,
                        354,
                        355,
                        356,
                        357,
                        358
                    ]
                ],
                "single": [],
                "title": "Undocumented Section Number (MSF2020)"
            },
            "088000": {
                "multi": [
                    [
                        327,
                        328,
                        329
                    ],
                    [
                        337,
                        338
                    ],
                    [
                        341,
                        342
                    ],
                    [
                        359,
                        360,
                        361,
                        362,
                        363,
                        364,
                        365,
                        366,
                        367,
                        368,
                        369
                    ]
                ],
                "single": [
                    3,
                    304,
                    310,
                    313,
                    321,
                    331,
                    335
                ],
                "title": "Glazing"
            },
            "089100": {
                "multi": [
                    [
                        370,
                        371,
                        372,
                        373
                    ]
                ],
                "single": [
                    3
                ],
                "title": "Louvers"
            }
        },
        "09": {
            "092116": {
                "multi": [
                    [
                        374,
                        375,
                        376,
                        377,
                        378,
                        379
                    ]
                ],
                "single": [
                    3,
                    387
                ],
                "title": "Gypsum Board Assemblies"
            },
            "092216": {
                "multi": [
                    [
                        380,
                        381,
                        382,
                        383,
                        384,
                        385,
                        386
                    ]
                ],
                "single": [
                    3,
                    374
                ],
                "title": "Non-Structural Metal Framing"
            },
            "093000": {
                "multi": [
                    [
                        387,
                        388,
                        389,
                        390,
                        391,
                        392,
                        393
                    ]
                ],
                "single": [
                    3
                ],
                "title": "Tiling"
            },
            "095000": {
                "multi": [],
                "single": [
                    402
                ],
                "title": "Ceilings"
            },
            "095100": {
                "multi": [
                    [
                        394,
                        395,
                        396,
                        397
                    ]
                ],
                "single": [
                    3
                ],
                "title": "Acoustical Ceilings"
            },
            "095460": {
                "multi": [
                    [
                        398,
                        399,
                        400,
                        401,
                        402
                    ]
                ],
                "single": [
                    3
                ],
                "title": "Undocumented Section Number (MSF2020)"
            },
            "096513": {
                "multi": [],
                "single": [
                    4,
                    403,
                    406,
                    417
                ],
                "title": "Resilient Base and Accessories"
            },
            "096513.23": {
                "multi": [
                    [
                        403,
                        404,
                        405,
                        406
                    ]
                ],
                "single": [],
                "title": "Resilient Stair Treads and Risers"
            },
            "096525": {
                "multi": [
                    [
                        407,
                        408,
                        409,
                        410
                    ]
                ],
                "single": [
                    4
                ],
                "title": "Undocumented Section Number (MSF2020)"
            },
            "096723": {
                "multi": [
                    [
                        411,
                        412,
                        413,
                        414,
                        415,
                        416
                    ]
                ],
                "single": [
                    4
                ],
                "title": "Resinous Flooring"
            },
            "096813": {
                "multi": [
                    [
                        417,
                        418,
                        419,
                        420,
                        421,
                        422
                    ]
                ],
                "single": [
                    4
                ],
                "title": "Tile Carpeting"
            },
            "099113": {
                "multi": [],
                "single": [
                    176,
                    187,
                    194,
                    944
                ],
                "title": "Exterior Painting"
            },
            "099123": {
                "multi": [
                    [
                        423,
                        424,
                        425,
                        426,
                        427,
                        428,
                        429,
                        430,
                        431,
                        432,
                        433,
                        434,
                        435
                    ]
                ],
                "single": [
                    4,
                    176,
                    187,
                    194,
                    304,
                    900,
                    914,
                    944,
                    1183
                ],
                "title": "Interior Painting"
            },
            "099600": {
                "multi": [],
                "single": [
                    187
                ],
                "title": "High-Performance Coatings"
            }
        },
        "10": {
            "101110": {
                "multi": [],
                "single": [
                    43
                ],
                "title": "Undocumented Section Number (MSF2020)"
            },
            "102030": {
                "multi": [
                    [
                        60,
                        61,
                        62,
                        63
                    ]
                ],
                "single": [],
                "title": "Undocumented Section Number (MSF2020)"
            },
            "102236": {
                "multi": [],
                "single": [
                    4
                ],
                "title": "Coiling Partitions"
            },
            "102239": {
                "multi": [
                    [
                        436,
                        437,
                        438,
                        439,
                        440,
                        441,
                        442
                    ]
                ],
                "single": [],
                "title": "Folding Panel Partitions"
            },
            "104320": {
                "multi": [],
                "single": [
                    63
                ],
                "title": "Undocumented Section Number (MSF2020)"
            },
            "104400": {
                "multi": [
                    [
                        443,
                        444,
                        445
                    ]
                ],
                "single": [
                    4
                ],
                "title": "Fire Protection Specialties"
            }
        },
        "12": {
            "120039": {
                "multi": [
                    [
                        45,
                        46,
                        47,
                        48
                    ]
                ],
                "single": [],
                "title": "Undocumented Section Number (MSF2020)"
            },
            "121713": {
                "multi": [],
                "single": [
                    39
                ],
                "title": "Etched Glass"
            },
            "122413": {
                "multi": [
                    [
                        446,
                        447,
                        448,
                        449
                    ]
                ],
                "single": [
                    4
                ],
                "title": "Roller Window Shades"
            },
            "123553": {
                "multi": [
                    [
                        450,
                        451,
                        452,
                        453,
                        454,
                        455,
                        456,
                        457
                    ]
                ],
                "single": [
                    4
                ],
                "title": "Laboratory Casework"
            }
        },
        "13": {
            "132000": {
                "multi": [],
                "single": [
                    753
                ],
                "title": "Special Purpose Rooms"
            },
            "132130": {
                "multi": [],
                "single": [
                    38
                ],
                "title": "Undocumented Section Number (MSF2020)"
            },
            "133413": {
                "multi": [
                    [
                        458,
                        459,
                        460,
                        461,
                        462,
                        463,
                        464,
                        465,
                        466,
                        467,
                        468,
                        469
                    ]
                ],
                "single": [
                    4
                ],
                "title": "Glazed Structures"
            },
            "133419": {
                "multi": [],
                "single": [
                    176
                ],
                "title": "Metal Building Systems"
            }
        },
        "21": {
            "210000": {
                "multi": [
                    [
                        470,
                        471,
                        472,
                        473,
                        474,
                        475,
                        476,
                        477,
                        478,
                        479,
                        480,
                        481,
                        482,
                        483,
                        484,
                        485,
                        486,
                        487,
                        488,
                        489,
                        490
                    ]
                ],
                "single": [
                    4
                ],
                "title": "Fire Suppression"
            },
            "210500": {
                "multi": [
                    [
                        491,
                        492,
                        493,
                        494,
                        495,
                        496,
                        497,
                        498
                    ]
                ],
                "single": [
                    4
                ],
                "title": "Common Work Results for Fire Suppression"
            },
            "210519": {
                "multi": [
                    [
                        499,
                        500,
                        501,
                        502,
                        503,
                        504,
                        505
                    ]
                ],
                "single": [
                    4
                ],
                "title": "Meters and Gauges for Fire-Suppression Systems"
            },
            "210529": {
                "multi": [
                    [
                        506,
                        507,
                        508,
                        509,
                        510
                    ]
                ],
                "single": [
                    4
                ],
                "title": "Hangers and Supports for Fire-Suppression Piping and Equipment"
            },
            "210553": {
                "multi": [
                    [
                        511,
                        512,
                        513
                    ]
                ],
                "single": [
                    4
                ],
                "title": "Identification for Fire-Suppression Piping and Equipment"
            },
            "210700": {
                "multi": [
                    [
                        514,
                        515,
                        516,
                        517
                    ]
                ],
                "single": [
                    4
                ],
                "title": "Fire Suppression Systems Insulation"
            },
            "211000": {
                "multi": [
                    [
                        518,
                        519,
                        520,
                        521
                    ]
                ],
                "single": [
                    4
                ],
                "title": "Water-Based Fire-Suppression Systems"
            },
            "211200": {
                "multi": [
                    [
                        522,
                        523,
                        524
                    ]
                ],
                "single": [
                    4
                ],
                "title": "Fire-Suppression Standpipes"
            }
        },
        "22": {
            "220000": {
                "multi": [
                    [
                        525,
                        526,
                        527,
                        528,
                        529,
                        530,
                        531,
                        532,
                        533,
                        534,
                        535,
                        536,
                        537,
                        538,
                        539,
                        540,
                        541,
                        542,
                        543,
                        544,
                        545,
                        546
                    ]
                ],
                "single": [
                    4
                ],
                "title": "Plumbing"
            },
            "220120": {
                "multi": [
                    [
                        9,
                        10,
                        11,
                        12,
                        13,
                        14,
                        15,
                        16,
                        17,
                        18
                    ],
                    [
                        20,
                        21,
                        22,
                        23,
                        24,
                        25,
                        26,
                        27,
                        28,
                        29,
                        30,
                        31
                    ],
                    [
                        33,
                        34
                    ],
                    [
                        38,
                        39,
                        40,
                        41,
                        42,
                        43,
                        44,
                        45,
                        46,
                        47,
                        48,
                        49,
                        50,
                        51,
                        52,
                        53,
                        54,
                        55,
                        56
                    ]
                ],
                "single": [
                    59
                ],
                "title": "Undocumented Section Number (MSF2020)"
            },
            "220500": {
                "multi": [
                    [
                        547,
                        548,
                        549,
                        550,
                        551,
                        552,
                        553,
                        554,
                        555
                    ]
                ],
                "single": [
                    4
                ],
                "title": "Common Work Results for Plumbing"
            },
            "220519": {
                "multi": [
                    [
                        556,
                        557,
                        558,
                        559
                    ]
                ],
                "single": [
                    4
                ],
                "title": "Meters and Gauges for Plumbing Piping"
            },
            "220523": {
                "multi": [
                    [
                        560,
                        561,
                        562,
                        563
                    ]
                ],
                "single": [
                    4
                ],
                "title": "General-Duty Valves for Plumbing Piping"
            },
            "220529": {
                "multi": [
                    [
                        564,
                        565,
                        566,
                        567,
                        568,
                        569,
                        570,
                        571
                    ]
                ],
                "single": [
                    4
                ],
                "title": "Hangers and Supports for Plumbing Piping and Equipment"
            },
            "220553": {
                "multi": [
                    [
                        572,
                        573,
                        574
                    ]
                ],
                "single": [
                    4
                ],
                "title": "Identification for Plumbing Piping and Equipment"
            },
            "220593": {
                "multi": [
                    [
                        575,
                        576,
                        577,
                        578,
                        579
                    ]
                ],
                "single": [
                    4
                ],
                "title": "Undocumented Section Number (MSF2020)"
            },
            "220719": {
                "multi": [
                    [
                        580,
                        581,
                        582,
                        583
                    ]
                ],
                "single": [
                    4
                ],
                "title": "Plumbing Piping Insulation"
            },
            "221116": {
                "multi": [
                    [
                        584,
                        585,
                        586,
                        587,
                        588,
                        589,
                        590,
                        591,
                        592
                    ]
                ],
                "single": [
                    4
                ],
                "title": "Domestic Water Piping"
            },
            "221119": {
                "multi": [
                    [
                        593,
                        594,
                        595,
                        596
                    ]
                ],
                "single": [
                    4
                ],
                "title": "Domestic Water Piping Specialties"
            },
            "221316": {
                "multi": [
                    [
                        597,
                        598,
                        599,
                        600,
                        601
                    ]
                ],
                "single": [
                    4
                ],
                "title": "Sanitary Waste and Vent Piping"
            },
            "221319": {
                "multi": [
                    [
                        602,
                        603
                    ]
                ],
                "single": [
                    4
                ],
                "title": "Sanitary Waste Piping Specialties"
            },
            "221413": {
                "multi": [
                    [
                        604,
                        605,
                        606
                    ]
                ],
                "single": [
                    5
                ],
                "title": "Facility Storm Drainage Piping"
            },
            "221423": {
                "multi": [
                    [
                        607,
                        608
                    ]
                ],
                "single": [
                    5
                ],
                "title": "Storm Drainage Piping Specialties"
            },
            "223333": {
                "multi": [
                    [
                        609,
                        610,
                        611
                    ]
                ],
                "single": [
                    5
                ],
                "title": "Light-Commercial Electric Domestic Water Heaters"
            },
            "224200": {
                "multi": [
                    [
                        612,
                        613,
                        614,
                        615,
                        616,
                        617,
                        618,
                        619
                    ]
                ],
                "single": [
                    5
                ],
                "title": "Commercial Plumbing Fixtures"
            },
            "226113": {
                "multi": [
                    [
                        620,
                        621,
                        622,
                        623
                    ]
                ],
                "single": [
                    5
                ],
                "title": "Compressed-Air Piping for Laboratory and Healthcare Facilities"
            },
            "226119": {
                "multi": [
                    [
                        624,
                        625
                    ]
                ],
                "single": [
                    5
                ],
                "title": "Compressed-Air Equipment for Laboratory and Healthcare Facilities"
            },
            "226213": {
                "multi": [
                    [
                        626,
                        627,
                        628
                    ]
                ],
                "single": [
                    5
                ],
                "title": "Vacuum Piping for Laboratory and Healthcare Facilities"
            },
            "226653": {
                "multi": [
                    [
                        629,
                        630,
                        631,
                        632
                    ]
                ],
                "single": [
                    5
                ],
                "title": "Laboratory Chemical-Waste and Vent Piping"
            },
            "226683": {
                "multi": [
                    [
                        633,
                        634
                    ]
                ],
                "single": [
                    5
                ],
                "title": "Chemical-Waste Tanks"
            }
        },
        "23": {
            "230000": {
                "multi": [
                    [
                        640,
                        641,
                        642,
                        643,
                        644,
                        645,
                        646,
                        647
                    ]
                ],
                "single": [
                    5
                ],
                "title": "Heating, Ventilating, and Air Conditioning (HVAC)"
            },
            "230500": {
                "multi": [
                    [
                        648,
                        649,
                        650,
                        651,
                        652,
                        653,
                        654,
                        655,
                        656
                    ]
                ],
                "single": [
                    5
                ],
                "title": "Common Work Results for HVAC"
            },
            "230513": {
                "multi": [
                    [
                        657,
                        658,
                        659,
                        660,
                        661,
                        662,
                        663,
                        664,
                        665,
                        666,
                        667,
                        668,
                        669
                    ]
                ],
                "single": [
                    5
                ],
                "title": "Common Motor Requirements for HVAC Equipment"
            },
            "230519": {
                "multi": [
                    [
                        670,
                        671
                    ]
                ],
                "single": [
                    5
                ],
                "title": "Meters and Gauges for HVAC Piping"
            },
            "230523": {
                "multi": [
                    [
                        672,
                        673,
                        674,
                        675,
                        676
                    ]
                ],
                "single": [
                    5
                ],
                "title": "General-Duty Valves for HVAC Piping"
            },
            "230529": {
                "multi": [
                    [
                        677,
                        678,
                        679,
                        680,
                        681,
                        682,
                        683,
                        684,
                        685
                    ]
                ],
                "single": [
                    5
                ],
                "title": "Hangers and Supports for HVAC Piping and Equipment"
            },
            "230548": {
                "multi": [
                    [
                        686,
                        687,
                        688,
                        689,
                        690,
                        691,
                        692,
                        693,
                        694,
                        695,
                        696,
                        697,
                        698,
                        699
                    ]
                ],
                "single": [
                    5
                ],
                "title": "Vibration and Seismic Controls for HVAC"
            },
            "230553": {
                "multi": [
                    [
                        700,
                        701,
                        702,
                        703
                    ]
                ],
                "single": [
                    5
                ],
                "title": "Identification for HVAC Piping and Equipment"
            },
            "230570": {
                "multi": [],
                "single": [
                    705
                ],
                "title": "Undocumented Section Number (MSF2020)"
            },
            "230580": {
                "multi": [
                    [
                        704,
                        705
                    ]
                ],
                "single": [
                    5
                ],
                "title": "Undocumented Section Number (MSF2020)"
            },
            "230593": {
                "multi": [
                    [
                        706,
                        707,
                        708,
                        709,
                        710,
                        711,
                        712,
                        713,
                        714,
                        715,
                        716,
                        717
                    ]
                ],
                "single": [
                    5
                ],
                "title": "Testing, Adjusting, and Balancing for HVAC"
            },
            "230713": {
                "multi": [
                    [
                        718,
                        719,
                        720,
                        721,
                        722,
                        723
                    ]
                ],
                "single": [
                    5,
                    727
                ],
                "title": "Duct Insulation"
            },
            "230719": {
                "multi": [
                    [
                        724,
                        725,
                        726,
                        727,
                        728
                    ]
                ],
                "single": [
                    5
                ],
                "title": "HVAC Piping Insulation"
            },
            "230801": {
                "multi": [],
                "single": [
                    794
                ],
                "title": "Undocumented Section Number (MSF2020)"
            },
            "230900": {
                "multi": [
                    [
                        729,
                        730,
                        731,
                        732,
                        733,
                        734,
                        735,
                        736,
                        737,
                        738,
                        739,
                        740,
                        741,
                        742,
                        743,
                        744,
                        745,
                        746,
                        747,
                        748,
                        749,
                        750,
                        751,
                        752,
                        753,
                        754,
                        755,
                        756,
                        757,
                        758,
                        759,
                        760,
                        761,
                        762,
                        763,
                        764,
                        765,
                        766,
                        767,
                        768,
                        769,
                        770,
                        771,
                        772,
                        773,
                        774,
                        775,
                        776,
                        777,
                        778,
                        779,
                        780,
                        781,
                        782,
                        783,
                        784,
                        785,
                        786,
                        787,
                        788,
                        789,
                        790,
                        791,
                        792,
                        793,
                        794,
                        795,
                        796
                    ]
                ],
                "single": [
                    5
                ],
                "title": "Instrumentation and Control for HVAC"
            },
            "230910": {
                "multi": [
                    [
                        755,
                        756,
                        757
                    ],
                    [
                        774,
                        775
                    ]
                ],
                "single": [
                    762
                ],
                "title": "Undocumented Section Number (MSF2020)"
            },
            "232113": {
                "multi": [
                    [
                        797,
                        798,
                        799,
                        800,
                        801,
                        802,
                        803,
                        804,
                        805,
                        806,
                        807,
                        808,
                        809,
                        810,
                        811
                    ]
                ],
                "single": [
                    5,
                    673
                ],
                "title": "Hydronic Piping"
            },
            "232123": {
                "multi": [
                    [
                        812,
                        813,
                        814
                    ]
                ],
                "single": [
                    5
                ],
                "title": "Hydronic Pumps"
            },
            "233113": {
                "multi": [
                    [
                        815,
                        816,
                        817,
                        818,
                        819,
                        820,
                        821,
                        822,
                        823,
                        824,
                        825,
                        826,
                        827
                    ]
                ],
                "single": [
                    5
                ],
                "title": "Metal Ducts"
            },
            "233300": {
                "multi": [
                    [
                        828,
                        829,
                        830,
                        831,
                        832,
                        833,
                        834,
                        835,
                        836
                    ]
                ],
                "single": [
                    5
                ],
                "title": "Air Duct Accessories"
            },
            "233416": {
                "multi": [
                    [
                        837,
                        838,
                        839,
                        840,
                        841,
                        842
                    ]
                ],
                "single": [
                    5
                ],
                "title": "Centrifugal HVAC Fans"
            },
            "233600": {
                "multi": [
                    [
                        843,
                        844,
                        845
                    ]
                ],
                "single": [
                    5
                ],
                "title": "Air Terminal Units"
            },
            "233713": {
                "multi": [
                    [
                        846,
                        847
                    ]
                ],
                "single": [
                    5
                ],
                "title": "Diffusers, Registers, and Grilles"
            },
            "233723": {
                "multi": [
                    [
                        848,
                        849
                    ]
                ],
                "single": [
                    5
                ],
                "title": "HVAC Gravity Ventilators"
            },
            "234100": {
                "multi": [
                    [
                        850,
                        851,
                        852,
                        853,
                        854
                    ]
                ],
                "single": [
                    5
                ],
                "title": "Particulate Air Filtration"
            },
            "237313": {
                "multi": [
                    [
                        855,
                        856,
                        857,
                        858,
                        859,
                        860,
                        861,
                        862,
                        863,
                        864
                    ]
                ],
                "single": [
                    5
                ],
                "title": "Modular Indoor Central-Station Air-Handling Units"
            },
            "237480": {
                "multi": [
                    [
                        865,
                        866,
                        867
                    ]
                ],
                "single": [
                    6
                ],
                "title": "Undocumented Section Number (MSF2020)"
            },
            "238126": {
                "multi": [
                    [
                        868,
                        869,
                        870,
                        871,
                        872
                    ]
                ],
                "single": [
                    6
                ],
                "title": "Split-System Air-Conditioners"
            },
            "238239": {
                "multi": [
                    [
                        873,
                        874,
                        875,
                        876
                    ]
                ],
                "single": [
                    6
                ],
                "title": "Unit Heaters"
            }
        },
        "26": {
            "260000": {
                "multi": [
                    [
                        877,
                        878,
                        879,
                        880,
                        881,
                        882,
                        883,
                        884,
                        885,
                        886,
                        887
                    ]
                ],
                "single": [
                    6
                ],
                "title": "Electrical"
            },
            "260010": {
                "multi": [
                    [
                        888,
                        889,
                        890,
                        891,
                        892,
                        893,
                        894,
                        895
                    ],
                    [
                        925,
                        926
                    ]
                ],
                "single": [
                    6,
                    905,
                    913,
                    940,
                    945,
                    958,
                    966,
                    975,
                    994,
                    998,
                    1001,
                    1013,
                    1019,
                    1028,
                    1035,
                    1038,
                    1066,
                    1079,
                    1092,
                    1095,
                    1100,
                    1105,
                    1113,
                    1133
                ],
                "title": "Undocumented Section Number (MSF2020)"
            },
            "260011": {
                "multi": [],
                "single": [
                    1113
                ],
                "title": "Undocumented Section Number (MSF2020)"
            },
            "260500": {
                "multi": [
                    [
                        896,
                        897,
                        898,
                        899,
                        900,
                        901,
                        902,
                        903,
                        904
                    ]
                ],
                "single": [
                    6,
                    882
                ],
                "title": "Common Work Results for Electrical"
            },
            "260519": {
                "multi": [
                    [
                        905,
                        906,
                        907,
                        908,
                        909,
                        910,
                        911,
                        912
                    ]
                ],
                "single": [
                    6,
                    882,
                    926,
                    945,
                    1040,
                    1136,
                    1144,
                    1168,
                    1312,
                    1331
                ],
                "title": "Low-Voltage Electrical Power Conductors and Cables"
            },
            "260523": {
                "multi": [
                    [
                        913,
                        914,
                        915,
                        916,
                        917,
                        918,
                        919,
                        920,
                        921,
                        922,
                        923,
                        924
                    ]
                ],
                "single": [
                    6,
                    905,
                    1331
                ],
                "title": "Control-Voltage Electrical Power Cables"
            },
            "260526": {
                "multi": [
                    [
                        925,
                        926,
                        927,
                        928,
                        929,
                        930,
                        931,
                        932,
                        933,
                        934,
                        935,
                        936,
                        937,
                        938,
                        939
                    ],
                    [
                        991,
                        992
                    ],
                    [
                        1331,
                        1332
                    ]
                ],
                "single": [
                    6,
                    882,
                    923,
                    1157,
                    1160
                ],
                "title": "Grounding and Bonding for Electrical Systems"
            },
            "260529": {
                "multi": [
                    [
                        940,
                        941,
                        942,
                        943,
                        944
                    ]
                ],
                "single": [
                    6,
                    883,
                    909,
                    957,
                    998,
                    1075,
                    1130,
                    1142,
                    1151,
                    1166
                ],
                "title": "Hangers and Supports for Electrical Systems"
            },
            "260533": {
                "multi": [],
                "single": [
                    909,
                    920,
                    922,
                    943,
                    1160,
                    1168
                ],
                "title": "Raceway and Boxes for Electrical Systems"
            },
            "260533.13": {
                "multi": [
                    [
                        945,
                        946,
                        947,
                        948,
                        949,
                        950,
                        951,
                        952,
                        953,
                        954,
                        955,
                        956,
                        957
                    ]
                ],
                "single": [
                    6,
                    883
                ],
                "title": "Conduit for Electrical Systems"
            },
            "260533.16": {
                "multi": [
                    [
                        958,
                        959,
                        960,
                        961,
                        962,
                        963,
                        964,
                        965
                    ]
                ],
                "single": [
                    6,
                    883
                ],
                "title": "Boxes for Electrical Systems"
            },
            "260533.23": {
                "multi": [
                    [
                        966,
                        967,
                        968,
                        969,
                        970
                    ]
                ],
                "single": [
                    6,
                    883
                ],
                "title": "Surface Raceways for Electrical Systems"
            },
            "260533.36": {
                "multi": [
                    [
                        971,
                        972,
                        973,
                        974
                    ]
                ],
                "single": [
                    6
                ],
                "title": "Undocumented Section Number (MSF2020)"
            },
            "260536": {
                "multi": [],
                "single": [
                    883
                ],
                "title": "Cable Trays for Electrical Systems"
            },
            "260543": {
                "multi": [
                    [
                        975,
                        976,
                        977,
                        978,
                        979,
                        980,
                        981,
                        982,
                        983,
                        984,
                        985,
                        986,
                        987,
                        988,
                        989,
                        990,
                        991,
                        992,
                        993
                    ]
                ],
                "single": [
                    6,
                    883,
                    936,
                    945
                ],
                "title": "Underground Ducts and Raceways for Electrical Systems"
            },
            "260544": {
                "multi": [
                    [
                        994,
                        995,
                        996,
                        997
                    ]
                ],
                "single": [
                    6,
                    911,
                    988
                ],
                "title": "Sleeves and Sleeve Seals for Electrical Raceways and Cabling"
            },
            "260548": {
                "multi": [
                    [
                        998,
                        999,
                        1000
                    ]
                ],
                "single": [
                    6,
                    943
                ],
                "title": "Vibration and Seismic Controls for Electrical Systems"
            },
            "260548.16": {
                "multi": [],
                "single": [
                    1074,
                    1081,
                    1088,
                    1119
                ],
                "title": "Seismic Controls for Electrical Systems"
            },
            "260553": {
                "multi": [
                    [
                        1001,
                        1002,
                        1003,
                        1004,
                        1005,
                        1006,
                        1007,
                        1008,
                        1009,
                        1010,
                        1011,
                        1012
                    ],
                    [
                        1129,
                        1130
                    ]
                ],
                "single": [
                    6,
                    883,
                    910,
                    923,
                    945,
                    958,
                    966,
                    979,
                    991,
                    1031,
                    1076,
                    1089,
                    1094,
                    1098,
                    1103,
                    1107,
                    1112,
                    1119,
                    1144,
                    1152,
                    1161,
                    1168,
                    1331
                ],
                "title": "Identification for Electrical Systems"
            },
            "260573": {
                "multi": [
                    [
                        884,
                        885
                    ]
                ],
                "single": [],
                "title": "Power System Studies"
            },
            "260573.13": {
                "multi": [
                    [
                        1013,
                        1014,
                        1015,
                        1016,
                        1017,
                        1018,
                        1019
                    ]
                ],
                "single": [
                    6,
                    884,
                    1022,
                    1028,
                    1030,
                    1032
                ],
                "title": "Short-Circuit Studies"
            },
            "260573.16": {
                "multi": [
                    [
                        1019,
                        1020,
                        1021,
                        1022,
                        1023,
                        1024,
                        1025,
                        1026,
                        1027,
                        1028
                    ]
                ],
                "single": [
                    6,
                    884,
                    895,
                    1013,
                    1030,
                    1032,
                    1078,
                    1090,
                    1122
                ],
                "title": "Coordination Studies"
            },
            "260573.19": {
                "multi": [
                    [
                        1028,
                        1029,
                        1030,
                        1031,
                        1032,
                        1033,
                        1034
                    ]
                ],
                "single": [
                    884,
                    895,
                    1002,
                    1013,
                    1019,
                    1066,
                    1129
                ],
                "title": "Arc-Flash Hazard Analysis"
            },
            "260800": {
                "multi": [
                    [
                        1035,
                        1036,
                        1037,
                        1038,
                        1039
                    ]
                ],
                "single": [
                    6,
                    884
                ],
                "title": "Commissioning of Electrical Systems"
            },
            "260913": {
                "multi": [],
                "single": [
                    1073
                ],
                "title": "Electrical Power Monitoring"
            },
            "260923": {
                "multi": [],
                "single": [
                    1092,
                    1162
                ],
                "title": "Lighting Control Devices"
            },
            "260943": {
                "multi": [
                    [
                        1040,
                        1041,
                        1042,
                        1043,
                        1044,
                        1045,
                        1046,
                        1047,
                        1048,
                        1049,
                        1050,
                        1051,
                        1052,
                        1053,
                        1054,
                        1055,
                        1056,
                        1057,
                        1058,
                        1059,
                        1060,
                        1061,
                        1062,
                        1063
                    ]
                ],
                "single": [
                    6,
                    884,
                    895,
                    1138,
                    1145,
                    1162
                ],
                "title": "Network Lighting Controls"
            },
            "260993": {
                "multi": [
                    [
                        1062,
                        1063,
                        1064,
                        1065
                    ]
                ],
                "single": [
                    6,
                    1040
                ],
                "title": "Undocumented Section Number (MSF2020)"
            },
            "262413": {
                "multi": [
                    [
                        1066,
                        1067,
                        1068,
                        1069,
                        1070,
                        1071,
                        1072,
                        1073,
                        1074,
                        1075,
                        1076,
                        1077,
                        1078
                    ]
                ],
                "single": [
                    6,
                    884,
                    895,
                    1133
                ],
                "title": "Switchboards"
            },
            "262416": {
                "multi": [
                    [
                        1079,
                        1080,
                        1081,
                        1082,
                        1083,
                        1084,
                        1085,
                        1086,
                        1087,
                        1088,
                        1089,
                        1090,
                        1091
                    ]
                ],
                "single": [
                    6,
                    885,
                    1133
                ],
                "title": "Panelboards"
            },
            "262726": {
                "multi": [],
                "single": [
                    917,
                    1133
                ],
                "title": "Wiring Devices"
            },
            "262726.11": {
                "multi": [
                    [
                        1092,
                        1093,
                        1094
                    ]
                ],
                "single": [
                    6,
                    885,
                    1040
                ],
                "title": "Undocumented Section Number (MSF2020)"
            },
            "262726.33": {
                "multi": [
                    [
                        1095,
                        1096,
                        1097,
                        1098,
                        1099,
                        1100
                    ]
                ],
                "single": [
                    6,
                    885,
                    1105
                ],
                "title": "Undocumented Section Number (MSF2020)"
            },
            "262726.37": {
                "multi": [
                    [
                        1100,
                        1101,
                        1102,
                        1103,
                        1104,
                        1105
                    ]
                ],
                "single": [
                    6,
                    885,
                    1095
                ],
                "title": "Undocumented Section Number (MSF2020)"
            },
            "262726.39": {
                "multi": [
                    [
                        1105,
                        1106,
                        1107,
                        1108
                    ]
                ],
                "single": [
                    6,
                    885,
                    1095,
                    1100
                ],
                "title": "Undocumented Section Number (MSF2020)"
            },
            "262813": {
                "multi": [
                    [
                        1109,
                        1110,
                        1111,
                        1112
                    ]
                ],
                "single": [
                    6,
                    659,
                    885
                ],
                "title": "Fuses"
            },
            "262816": {
                "multi": [
                    [
                        1113,
                        1114,
                        1115,
                        1116,
                        1117,
                        1118,
                        1119,
                        1120,
                        1121,
                        1122,
                        1123
                    ]
                ],
                "single": [
                    7,
                    660,
                    885
                ],
                "title": "Enclosed Switches and Circuit Breakers"
            },
            "262913": {
                "multi": [],
                "single": [
                    657,
                    660
                ],
                "title": "Enclosed Controllers"
            },
            "262913.03": {
                "multi": [
                    [
                        1124,
                        1125,
                        1126,
                        1127,
                        1128,
                        1129,
                        1130,
                        1131,
                        1132
                    ]
                ],
                "single": [
                    7,
                    885
                ],
                "title": "Undocumented Section Number (MSF2020)"
            },
            "262923": {
                "multi": [],
                "single": [
                    657
                ],
                "title": "Variable-Frequency Motor Controllers"
            },
            "264313": {
                "multi": [
                    [
                        1133,
                        1134,
                        1135,
                        1136,
                        1137
                    ]
                ],
                "single": [
                    7,
                    885,
                    895
                ],
                "title": "Surge Protective Devices for Low-Voltage Electrical Power Circuits"
            },
            "265119": {
                "multi": [
                    [
                        1138,
                        1139,
                        1140,
                        1141,
                        1142,
                        1143,
                        1144,
                        1145
                    ]
                ],
                "single": [
                    7,
                    885
                ],
                "title": "LED Interior Lighting"
            },
            "265213": {
                "multi": [],
                "single": [
                    886
                ],
                "title": "Emergency and Exit Lighting"
            },
            "265219": {
                "multi": [
                    [
                        1146,
                        1147,
                        1148,
                        1149,
                        1150,
                        1151,
                        1152,
                        1153
                    ]
                ],
                "single": [
                    7
                ],
                "title": "Undocumented Section Number (MSF2020)"
            },
            "265613": {
                "multi": [
                    [
                        1154,
                        1155,
                        1156,
                        1157,
                        1158,
                        1159,
                        1160,
                        1161,
                        1162
                    ]
                ],
                "single": [
                    7,
                    886
                ],
                "title": "Lighting Poles and Standards"
            },
            "265619": {
                "multi": [
                    [
                        1162,
                        1163,
                        1164,
                        1165,
                        1166,
                        1167,
                        1168,
                        1169
                    ]
                ],
                "single": [
                    7,
                    886,
                    895
                ],
                "title": "LED Exterior Lighting"
            }
        },
        "27": {
            "270000": {
                "multi": [
                    [
                        1170,
                        1171,
                        1172,
                        1173,
                        1174,
                        1175,
                        1176,
                        1177,
                        1178
                    ]
                ],
                "single": [
                    7
                ],
                "title": "Communications"
            },
            "270500": {
                "multi": [
                    [
                        1179,
                        1180,
                        1181,
                        1182,
                        1183,
                        1184,
                        1185,
                        1186,
                        1187,
                        1188,
                        1189,
                        1190,
                        1191
                    ]
                ],
                "single": [
                    7
                ],
                "title": "Common Work Results for Communications"
            },
            "270526": {
                "multi": [
                    [
                        1192,
                        1193,
                        1194,
                        1195,
                        1196,
                        1197,
                        1198,
                        1199,
                        1200,
                        1201,
                        1202
                    ]
                ],
                "single": [
                    7,
                    927,
                    1243,
                    1271,
                    1274,
                    1288,
                    1306
                ],
                "title": "Grounding and Bonding for Communications Systems"
            },
            "270528": {
                "multi": [
                    [
                        1203,
                        1204,
                        1205,
                        1206,
                        1207,
                        1208,
                        1209,
                        1210,
                        1211,
                        1212,
                        1213,
                        1214,
                        1215,
                        1216,
                        1217,
                        1218
                    ],
                    [
                        1306,
                        1307
                    ]
                ],
                "single": [
                    7,
                    1199,
                    1223,
                    1272,
                    1289
                ],
                "title": "Pathways for Communications Systems"
            },
            "270529": {
                "multi": [
                    [
                        1219,
                        1220,
                        1221,
                        1222,
                        1223,
                        1224,
                        1225
                    ]
                ],
                "single": [
                    7,
                    1214,
                    1274,
                    1289,
                    1307
                ],
                "title": "Hangers and Supports for Communications Systems"
            },
            "270534": {
                "multi": [
                    [
                        1226,
                        1227,
                        1228,
                        1229,
                        1230,
                        1231,
                        1232,
                        1233,
                        1234
                    ]
                ],
                "single": [
                    7
                ],
                "title": "Undocumented Section Number (MSF2020)"
            },
            "270536": {
                "multi": [
                    [
                        1235,
                        1236,
                        1237,
                        1238,
                        1239,
                        1240,
                        1241,
                        1242,
                        1243,
                        1244
                    ]
                ],
                "single": [
                    7,
                    1266,
                    1289,
                    1307
                ],
                "title": "Cable Trays for Communications Systems"
            },
            "270553": {
                "multi": [
                    [
                        1245,
                        1246,
                        1247,
                        1248
                    ]
                ],
                "single": [
                    7,
                    1197,
                    1241,
                    1273,
                    1291,
                    1309,
                    1332
                ],
                "title": "Identification for Communications Systems"
            },
            "270800": {
                "multi": [
                    [
                        1249,
                        1250,
                        1251,
                        1252,
                        1253,
                        1254,
                        1255,
                        1256,
                        1257,
                        1258,
                        1259,
                        1260,
                        1261,
                        1262,
                        1263,
                        1264,
                        1265
                    ]
                ],
                "single": [
                    7
                ],
                "title": "Commissioning of Communications"
            },
            "271100": {
                "multi": [
                    [
                        1266,
                        1267,
                        1268,
                        1269,
                        1270,
                        1271,
                        1272,
                        1273
                    ]
                ],
                "single": [
                    7,
                    1307
                ],
                "title": "Communications Equipment Room Fittings"
            },
            "271123": {
                "multi": [
                    [
                        1274,
                        1275,
                        1276,
                        1277,
                        1278,
                        1279,
                        1280,
                        1281
                    ]
                ],
                "single": [
                    7
                ],
                "title": "Communications Cable Management and Ladder Rack"
            },
            "271313": {
                "multi": [
                    [
                        1282,
                        1283,
                        1284,
                        1285,
                        1286,
                        1287,
                        1288,
                        1289,
                        1290,
                        1291,
                        1292,
                        1293
                    ]
                ],
                "single": [
                    7
                ],
                "title": "Communications Copper Backbone Cabling"
            },
            "271323": {
                "multi": [
                    [
                        1294,
                        1295,
                        1296,
                        1297
                    ]
                ],
                "single": [
                    7
                ],
                "title": "Communications Optical Fiber Backbone Cabling"
            },
            "271513": {
                "multi": [
                    [
                        1298,
                        1299,
                        1300,
                        1301,
                        1302,
                        1303,
                        1304,
                        1305,
                        1306,
                        1307,
                        1308,
                        1309,
                        1310,
                        1311
                    ]
                ],
                "single": [
                    7,
                    921,
                    1266,
                    1291
                ],
                "title": "Communications Copper Horizontal Cabling"
            }
        },
        "28": {
            "284621": {
                "multi": [
                    [
                        1312,
                        1313,
                        1314,
                        1315,
                        1316,
                        1317,
                        1318,
                        1319,
                        1320,
                        1321,
                        1322,
                        1323,
                        1324,
                        1325,
                        1326,
                        1327,
                        1328,
                        1329,
                        1330,
                        1331,
                        1332,
                        1333,
                        1334
                    ]
                ],
                "single": [
                    7,
                    886
                ],
                "title": "Fire-Alarm Control Units and Related Equipment"
            },
            "284621.11": {
                "multi": [],
                "single": [
                    910
                ],
                "title": "Undocumented Section Number (MSF2020)"
            }
        },
        "31": {
            "311000": {
                "multi": [],
                "single": [
                    985
                ],
                "title": "Site Clearing"
            },
            "312000": {
                "multi": [
                    [
                        990,
                        991
                    ]
                ],
                "single": [
                    126,
                    986,
                    988
                ],
                "title": "Earth Moving"
            }
        },
        "32": {
            "321313": {
                "multi": [],
                "single": [
                    126
                ],
                "title": "Concrete Paving"
            },
            "321316": {
                "multi": [],
                "single": [
                    126
                ],
                "title": "Decorative Concrete Paving"
            },
            "329200": {
                "multi": [],
                "single": [
                    986
                ],
                "title": "Turf and Grasses"
            },
            "329300": {
                "multi": [],
                "single": [
                    986
                ],
                "title": "Plants"
            }
        }
    },
    "text_and_rasterize": {
        "attempted_uploads": 1374,
        "dpi": 200,
        "end_index": None,
        "grayscale": False,
        "indexes_with_no_text_or_image": [],
        "rasterize_all": False,
        "runtime": "0:00:32",
        "spec_id": "af0762c9-64a7-4f06-a996-922d1d39fcb1",
        "start_index": 0,
        "status_code": 200,
        "success_rate": 100.0,
        "successful_uploads": 1374,
        "total_indexes_with_no_text_or_image": 0,
        "unsuccessful_uploads": "No unsuccessful uploads"
    }
}

AI_MAX_IN_FLIGHT = 6
S3_MAX_IN_FLIGHT = 25

ai_sem = asyncio.Semaphore(AI_MAX_IN_FLIGHT)
s3_sem = asyncio.Semaphore(S3_MAX_IN_FLIGHT)


class PageClassification(BaseModel):
    is_primary: bool = Field(
        description="Whether these pages contain the primary specification body for this section"
    )
    confidence: float = Field(
        description="Confidence level in the classification between 0 and 1"
    )
    reasoning: str = Field(
        description="Brief explanation of the classification decision"
    )
    pages_analyzed: list[int] = Field(
        description="List of page numbers that were analyzed"
    )


async def classify_block_ai(
    pages_to_analyze: list[int],
    section_number: str,
    spec_id: str,
    s3: S3Bucket,
    s3_client: any
) -> dict:
    system_prompt = """You are classifying construction specification pages.

Determine if these pages contain the PRIMARY specification body for the given section number, or if they are just references/context.

PRIMARY specification content has:
- Section title header (e.g., "SECTION 03 30 00 - CAST-IN-PLACE CONCRETE")
- CSI structure: "PART 1 - GENERAL", "PART 2 - PRODUCTS", "PART 3 - EXECUTION"
- Dense technical requirements, materials, installation procedures
- Numbered subsections (1.1, 1.2, 2.1, etc.)
- Submittal requirements, quality standards, testing procedures

NOT primary content:
- Table of contents (just lists section numbers)
- Single-line references ("See Section 03 30 00")
- Substitution/product lists
- Cross-references from other sections
- Divider pages with minimal content

Note: You may only see the first 2-3 pages of a longer section. If those pages show clear PRIMARY indicators, classify as primary."""

    # Fetch pages using generator
    start_index = min(pages_to_analyze)
    end_index = max(pages_to_analyze) + 1

    pages_dict = {}
    async for page in s3.get_converted_pages_generator_with_client(
        spec_id, s3_client, start_index, end_index
    ):
        if page["page_index"] in pages_to_analyze:
            pages_dict[page["page_index"]] = page

    # Build content blocks
    content = []
    for page_num in sorted(pages_to_analyze):
        page = pages_dict[page_num]
        text = page.get("text", "").strip()
        image_bytes = page.get("bytes")

        if text:
            content.append({
                "type": "text",
                "text": f"===== PAGE {page_num} TEXT =====\n{text}\n"
            })

        if image_bytes:
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": image_bytes
                }
            })

    content.append({
        "type": "text",
        "text": f"Section number being analyzed: {section_number}"
    })

    # Call Claude
    res = await client.beta.messages.parse(
        model="claude-sonnet-4-5-20250929",
        max_tokens=1024,
        betas=["structured-outputs-2025-11-13"],
        output_format=PageClassification,
        system=system_prompt,
        messages=[{"role": "user", "content": content}]
    )

    return res.parsed_output.model_dump()


# Classifies pages for a section as primary, referential, or other
async def classify_section(
    section_number: str,
    section_data: dict,
    spec_id: str,
    s3: S3Bucket,
    s3_client: any
) -> list[dict]:
    results = []

    # Classify each contiguous block (first 2 pages only)
    for block in section_data["multi"]:
        first_two = block[:2]
        result = await classify_block_ai(
            pages_to_analyze=first_two,
            section_number=section_number,
            spec_id=spec_id,
            s3=s3,
            s3_client=s3_client
        )
        result["block_type"] = "contiguous"
        result["full_block"] = block  # Store full block for later use
        results.append(result)

    # Classify each isolated page
    for page in section_data["single"]:
        result = await classify_block_ai(
            pages_to_analyze=[page],
            section_number=section_number,
            spec_id=spec_id,
            s3=s3,
            s3_client=s3_client
        )
        result["block_type"] = "isolated"
        results.append(result)

    return results

# Classifies all sections for a specification into primary, referential, or other
# Each division is ran one at a time. i.e. run through division 01 first and wait for it to complete before running division 02.
async def classify_all_sections_by_division(
    spec_id: str,
    section_data: dict,
    s3: S3Bucket,
    s3_client: any,
    max_concurrent: int = 5,
    delay_between_calls: float = 5.0,
    delay_between_divisions: float = 10.0,
    rate_limit_pause: float = 5.0  # Pause everything on 429
) -> dict:
    """
    Classify all sections with rate limiting
    """

    all_results = {}
    divisions = list(section_data["section_page_index"].keys())
    semaphore = asyncio.Semaphore(max_concurrent)

    logger.info(f"Total divisions to process: {len(divisions)}")
    logger.info(f"Max concurrent API calls: {max_concurrent}")
    logger.info(f"Delay between calls: {delay_between_calls}s")
    logger.info(f"Delay between divisions: {delay_between_divisions}s\n")

    async def classify_with_throttle(section_num, section_info):
        """Classify a section with rate limiting"""
        async with semaphore:
            try:
                await asyncio.sleep(delay_between_calls)

                result = await classify_section(
                    section_number=section_num,
                    section_data=section_info,
                    spec_id=spec_id,
                    s3=s3,
                    s3_client=s3_client
                )
                return section_num, section_info, result, None

            except RateLimitError as e:
                # Return special error type for 429s
                return section_num, section_info, None, ("RATE_LIMIT", str(e))
            except Exception as e:
                return section_num, section_info, None, ("ERROR", str(e))

    # Process each division sequentially
    for div_idx, division in enumerate(divisions, 1):
        div_sections = section_data["section_page_index"][division]

        logger.info(f"\n{'='*60}")
        logger.info(f"Division {div_idx}/{len(divisions)}: {division}")
        logger.info(f"{'='*60}")
        logger.info(f"Sections in this division: {len(div_sections)}")

        all_results[division] = {}

        # Create tasks for all sections in this division
        tasks = [
            classify_with_throttle(section_num, section_info)
            for section_num, section_info in div_sections.items()
        ]

        # Process all sections (throttled by semaphore)
        results = await asyncio.gather(*tasks)

        # Check for rate limits
        rate_limited_sections = []

        # Process results
        for section_num, section_info, classification_results, error in results:
            if error:
                if isinstance(error, tuple) and error[0] == "RATE_LIMIT":
                    # Track rate limited sections for retry
                    rate_limited_sections.append((section_num, section_info))
                    logger.warning(f"  ⚠ {section_num}: Rate limited")
                else:
                    error_msg = error[1] if isinstance(error, tuple) else error
                    logger.error(f"  ✗ {section_num}: {error_msg}")
                    all_results[division][section_num] = {
                        "section_name": section_info["title"],
                        "error": error_msg
                    }
                continue

            # Extract primary/reference pages
            primary_pages = []
            reference_pages = []

            for result in classification_results:
                if result["is_primary"]:
                    if result["block_type"] == "contiguous":
                        primary_pages.extend(result["full_block"])
                    else:
                        primary_pages.extend(result["pages_analyzed"])
                else:
                    reference_pages.extend(result["pages_analyzed"])

            all_results[division][section_num] = {
                "section_name": section_info["title"],
                "primary_pages": sorted(list(set(primary_pages))),
                "reference_pages": sorted(list(set(reference_pages))),
                "classification_results": classification_results
            }

            logger.info(f"  ✓ {section_num}: {len(primary_pages)} primary, {len(reference_pages)} reference")

        # If we hit rate limits, pause and retry
        if rate_limited_sections:
            logger.warning(f"\n⚠ Hit rate limits on {len(rate_limited_sections)} sections")
            logger.warning(f"Pausing for {rate_limit_pause}s then retrying...")
            await asyncio.sleep(rate_limit_pause)

            # Retry rate limited sections
            retry_tasks = [
                classify_with_throttle(section_num, section_info)
                for section_num, section_info in rate_limited_sections
            ]

            retry_results = await asyncio.gather(*retry_tasks)

            # Process retry results
            for section_num, section_info, classification_results, error in retry_results:
                if error:
                    error_msg = error[1] if isinstance(error, tuple) else error
                    logger.error(f"  ✗ {section_num} (retry failed): {error_msg}")
                    all_results[division][section_num] = {
                        "section_name": section_info["title"],
                        "error": error_msg
                    }
                    continue

                # Extract primary/reference pages
                primary_pages = []
                reference_pages = []

                for result in classification_results:
                    if result["is_primary"]:
                        if result["block_type"] == "contiguous":
                            primary_pages.extend(result["full_block"])
                        else:
                            primary_pages.extend(result["pages_analyzed"])
                    else:
                        reference_pages.extend(result["pages_analyzed"])

                all_results[division][section_num] = {
                    "section_name": section_info["title"],
                    "primary_pages": sorted(list(set(primary_pages))),
                    "reference_pages": sorted(list(set(reference_pages))),
                    "classification_results": classification_results
                }

                logger.info(f"  ✓ {section_num} (retried): {len(primary_pages)} primary, {len(reference_pages)} reference")

        logger.info(f"\nDivision {division} complete")

        # Add delay before next division (except after last one)
        if div_idx < len(divisions):
            logger.info(f"Waiting {delay_between_divisions}s before next division...")
            await asyncio.sleep(delay_between_divisions)

    return all_results


async def main():
    """Run full classification"""

    spec_id = "af0762c9-64a7-4f06-a996-922d1d39fcb1"
    s3 = S3Bucket()

    async with s3.s3_client() as s3_client:
        logger.info("="*60)
        logger.info("CLASSIFICATION PROCESS STARTED")
        logger.info("="*60)
        logger.info(f"Project ID: {spec_id}\n")

        results = await classify_all_sections_by_division(
            spec_id=spec_id,
            section_data=dict_of_sections_and_pages,
            s3=s3,
            s3_client=s3_client,
            max_concurrent=5,
            delay_between_calls=5.0,
            delay_between_divisions=10.0,
            rate_limit_pause=10.0
        )

        # Save results
        output_file = f"classification_results_{spec_id}.json"
        with open(output_file, "w") as f:
            json.dump(results, f, indent=2)

        logger.info(f"\n{'='*60}")
        logger.info("CLASSIFICATION COMPLETE")
        logger.info(f"{'='*60}")
        logger.info(f"Results saved to: {output_file}\n")

        # Summary
        total_sections = sum(len(div) for div in results.values())
        sections_with_primary = sum(
            1 for div in results.values()
            for sec in div.values()
            if sec.get("primary_pages")
        )
        errors = sum(
            1 for div in results.values()
            for sec in div.values()
            if "error" in sec
        )

        logger.info("Summary:")
        logger.info(f"  Total sections: {total_sections}")
        logger.info(f"  With primary content: {sections_with_primary}")
        logger.info(
            f"  References only: {total_sections - sections_with_primary - errors}")
        logger.info(f"  Errors: {errors}")

asyncio.run(main())
