import os
import pandas as pd
import geopandas as gpd
from shapely import wkt
from shapely.geometry import Point

def load_mesh_data(mesh_data_path: str, encoding: str = 'shift_jis') -> gpd.GeoDataFrame:
    """
    メッシュデータ（ポリゴン）を読み込み、GeoDataFrameとして返す。

    :param mesh_data_path: メッシュデータのCSVファイルパス
    :param encoding: ファイルの文字コード (デフォルト: shift_jis)
    :return: メッシュデータを格納したGeoDataFrame
    """
    if not os.path.exists(mesh_data_path):
        raise FileNotFoundError(f"メッシュデータファイルが見つかりません: {mesh_data_path}")

    mesh_data = pd.read_csv(mesh_data_path, encoding=encoding)
    # WKT列をShapelyのPolygonオブジェクトに変換
    mesh_data["geometry"] = mesh_data["WKT"].apply(wkt.loads)
    mesh_gdf = gpd.GeoDataFrame(mesh_data, geometry="geometry")
    return mesh_gdf

def is_blank(value) -> bool:
    """
    Excelセル等から読み込んだ値が空かどうかを判定する。
    pandas的に NaN である場合や、文字列が空白の場合も True を返す。
    """
    return pd.isna(value) or str(value).strip() == ""

def parse_percentage(value) -> float:
    """
    ユーザー入力の値 (例: '30', '30%', '0.5') をパーセントとして解釈し、
    小数（割合）の形で返す関数。

    - '30' や '30%' は 0.3 として返す
    - '0.5' は 0.5 (50%) として返す
    - '100' や '100%' は 1.0 として返す
    """
    s = str(value).strip()
    # もし末尾に '%' があれば除去
    if s.endswith('%'):
        s = s[:-1]  # '%'を取り除く

    # 数値に変換
    f = float(s)

    # 1 より大きい場合は百分率とみなし 100 で割る
    # 例: '30' → 30.0 > 1 → 30 / 100 = 0.3
    if f > 1.0:
        f = f / 100.0

    return f

def main():
    # -------------------------------------------------
    # 1. Excelファイルから必要データを読み込む
    # -------------------------------------------------
    excel_path = "input/雪災リスク分析_分析条件シート.xlsx"

    # シートをDataFrameとして読み込む (1枚目のシート, header=Noneで生データとして取得)
    df_excel = pd.read_excel(excel_path, sheet_name=0, header=None)

    # 指定セルから値を取得 (Excelは0-basedインデックス)
    panel_name = df_excel.iloc[14, 3]   # D15行目
    latitude   = df_excel.iloc[16, 3]   # D17行目
    longitude  = df_excel.iloc[17, 3]   # D18行目
    cost       = df_excel.iloc[19, 3]   # D20行目

    # 架台/モジュール/電気設備/その他
    kadai   = df_excel.iloc[36, 3]  # D37行目
    module  = df_excel.iloc[37, 3]  # D38行目
    denki   = df_excel.iloc[38, 3]  # D39行目
    sonota  = df_excel.iloc[39, 3]  # D40行目

    # -------------------------------------------------
    # 2. 空白 or 非空（パーセント解釈）判定しながら値を決定
    # -------------------------------------------------
    if is_blank(kadai):
        # 空白なら Cost * 0.5
        kadai = cost * 0.5
    else:
        # 空白でなければ、ユーザー入力値をパーセントとして解釈して Cost と掛ける
        frac = parse_percentage(kadai)  # 0.5 など
        kadai = cost * frac

    if is_blank(module):
        module = cost * 0.2
    else:
        frac = parse_percentage(module)
        module = cost * frac

    if is_blank(denki):
        denki = cost * 0.1
    else:
        frac = parse_percentage(denki)
        denki = cost * frac

    if is_blank(sonota):
        sonota = cost * 0.1
    else:
        frac = parse_percentage(sonota)
        sonota = cost * frac

    # -------------------------------------------------
    # 3. ソーラーパネルのデータをDataFrame化 → GeoDataFrame化
    # -------------------------------------------------
    solar_panel_data = {
        "PanelName": [panel_name],
        "緯度":       [latitude],
        "経度":       [longitude],
        "Cost":      [cost],
        "架台":       [kadai],
        "モジュール":  [module],
        "電気設備":   [denki],
        "その他":     [sonota]
    }
    solar_panel_df = pd.DataFrame(solar_panel_data)

    # 経度・緯度から Point を生成
    solar_panel_df["geometry"] = solar_panel_df.apply(
        lambda row: Point(row["経度"], row["緯度"]), axis=1
    )
    solar_panel_gdf = gpd.GeoDataFrame(solar_panel_df, geometry="geometry")

    # -------------------------------------------------
    # 4. メッシュデータの読み込み
    # -------------------------------------------------
    mesh_data_path = "input/sample_mesh_data.csv"
    mesh_gdf = load_mesh_data(mesh_data_path, encoding="shift_jis")

    # -------------------------------------------------
    # 5. 空間結合
    # -------------------------------------------------
    # GeoPandas 0.10以降は predicate="within"
    # 古いバージョンの場合は op="within" を使用
    result = gpd.sjoin(solar_panel_gdf, mesh_gdf, how="left", predicate="within")

    # メッシュデータの "id" を "mesh_id" にリネーム
    result = result.rename(columns={"id": "mesh_id"})

    # -------------------------------------------------
    # 6. 出力カラムの選定
    # -------------------------------------------------
    output_columns = [
        "mesh_id",
        "PanelName",
        "緯度",
        "経度",
        "Cost",
        "架台",
        "モジュール",
        "電気設備",
        "その他"
    ]
    output_df = result[output_columns].copy()

    # -------------------------------------------------
    # 7. CSVファイルへの書き出し
    # -------------------------------------------------
    output_folder = "output"
    os.makedirs(output_folder, exist_ok=True)

    output_file_path = os.path.join(output_folder, "solar_panel_with_mesh_id.csv")
    output_df.to_csv(output_file_path, index=False, encoding="shift_jis")

    print(f"結果が {output_file_path} に保存されました。")

if __name__ == "__main__":
    main()
