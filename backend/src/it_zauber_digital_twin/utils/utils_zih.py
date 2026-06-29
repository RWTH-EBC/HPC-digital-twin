import polars as pl


def calc_KPIs(
    input_data: pl.DataFrame, attr: str
) -> tuple[pl.Series, pl.Series, pl.Series]:
    E_IT = (
        input_data[f"LZR.DLR.Racks-AK.HPC-Wirkleistung{attr}"]
        + input_data[f"LZR.capella.Racks-E12.Wirkleistung{attr}"]
        + input_data[f"LZR.alpha.Racks.HPC-Wirkleistung{attr}"]
        + input_data[f"LZR.barnard.Racks-E12.Wirkleistung{attr}"]
    )

    E_DC = (
        E_IT
        # pumps
        ## KKR01
        + input_data[f"LZR.E64.ABG10.B83.W{attr}"]
        + input_data[f"LZR.E69.ABG03.B83.W{attr}"]
        ## KKR02
        + input_data[f"LZR.E64.ABG11.B83.W{attr}"]
        + input_data[f"LZR.E69.ABG01.B83.W{attr}"]
        ## KKR03
        + input_data[f"LZR.E64.ABG12.B83.W{attr}"]
        + input_data[f"LZR.E69.ABG02.B83.W{attr}"]
        ## KKR04
        + input_data[f"LZR.E64.ABG13.B83.W{attr}"]
        + input_data[f"LZR.E69.ABG04.B83.W{attr}"]
        ## H01.WUE
        + input_data[f"LZR.E74.EIN01.B83.W{attr}"]
        ## H01.HKR01/02/ABG01
        + input_data[f"LZR.E72.EIN01.B83.W{attr}"]
        ## K02
        + input_data[f"LZR.E60.ABG10.B83.W{attr}"]
        + input_data[f"LZR.E60.ABG11.B83.W{attr}"]
        + input_data[f"LZR.E60.ABG12.B83.W{attr}"]
        + input_data[f"LZR.E60.ABG07.B83.W{attr}"]
        + input_data[f"LZR.E60.ABG08.B83.W{attr}"]
        + input_data[f"LZR.E60.ABG09.B83.W{attr}"]
        # RKW
        + input_data[f"LZR.E12.ABG02.B83.W{attr}"]
        + input_data[f"LZR.E15.ABG03.B83.W{attr}"]
        # Heat pumps
        + input_data[f"WPG.H01.WPA01.B83{attr}"]
        + input_data[f"WPG.H01.WPA02.B83{attr}"]
        + input_data[f"WPG.H01.WPA03.B83{attr}"]
        # LZR Overhead (proportional)
        + 0.03328 * E_IT
        # USV-loss (proportional)
        + 0.05694 * E_IT
        # K04 (proportional)
        + 0.01394 * E_IT
    )

    E_Reuse = (
        # Heating
        ## LZR
        input_data[f"LZR.H01.HKR01.B29.LN{attr}"]
        + input_data[f"LZR.H01.HKR02.B29.LN{attr}"]
        ## KRO
        + input_data[f"LZR.H01.ABG01.B29.MB{attr}"]
        ## DLR
        + input_data[f"DLR.H01.WUE01.B29.MB{attr}"]
        ## Heat pumps district heating
        + input_data[f"WPG.H01.ABG01.B29{attr}"]
    )

    PUE = (E_DC / E_IT).alias(f"pue{attr}")
    ERF = (E_Reuse / E_DC).alias(f"erf{attr}")
    ERE = ((1 - ERF) * PUE).alias(f"ere{attr}")

    return PUE, ERF, ERE
