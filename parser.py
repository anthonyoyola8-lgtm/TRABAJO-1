import pandas as pd

COLS = ["group", "suc", "sol", "rec", "norec", "cumpl",
        "sol_a", "rec_a", "recreal_a", "norec_a", "cumpl_a"]


def parse_export(file) -> pd.DataFrame:
    """Convierte el export jerárquico (ag-grid) en una tabla plana.

    Jerarquía: -> TIA -> PROVEEDOR -> ESTADÍSTICO -> PRODUCTO, y debajo
    de cada producto vienen filas por sucursal.
    """
    raw = pd.read_excel(file, header=None, skiprows=2)
    raw = raw.iloc[:, :11]
    raw.columns = COLS

    rows, prov, estad, prod = [], None, None, None
    for r in raw.itertuples(index=False):
        if isinstance(r.group, str):
            parts = [p.strip() for p in r.group.split("->") if p.strip()]
            lvl = len(parts)
            if lvl == 2:
                prov, estad, prod = parts[1], None, None
            elif lvl == 3:
                estad, prod = parts[2], None
            elif lvl == 4:
                prod = parts[3]
                prov, estad = parts[1], parts[2]
        elif pd.notna(r.suc) and prod is not None:
            rows.append((prov, estad, prod, str(int(r.suc)),
                         r.sol, r.rec, r.norec, r.sol_a, r.rec_a, r.norec_a))

    df = pd.DataFrame(rows, columns=[
        "Proveedor", "Estadístico", "Producto", "Sucursal",
        "Solicitado", "Recibido", "No Recibido",
        "Solicitado_ant", "Recibido_ant", "No Recibido_ant"])
    return df
