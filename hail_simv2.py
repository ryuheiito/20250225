import numpy as np  # NumPy をインポート
import pandas as pd  # Pandas をインポート
from tqdm import tqdm  # 進行状況を表示
from scipy.stats import norm
from scipy.interpolate import interp1d

def create_hail_pdf(mean, variance, num_points=500):
    hail_sizes = np.linspace(max(0, mean - 3 * np.sqrt(variance)), mean + 3 * np.sqrt(variance), num_points)
    pdf_values = norm.pdf(hail_sizes, loc=mean, scale=np.sqrt(variance))
    pdf_values /= np.sum(pdf_values)
    return hail_sizes, pdf_values

import numpy as np  # NumPy をインポート
import pandas as pd  # Pandas をインポート
from tqdm import tqdm  # 進行状況を表示
from scipy.stats import norm
from scipy.interpolate import interp1d

def create_hail_pdf(mean, variance, num_points=500):
    hail_sizes = np.linspace(max(0, mean - 3 * np.sqrt(variance)), mean + 3 * np.sqrt(variance), num_points)
    pdf_values = norm.pdf(hail_sizes, loc=mean, scale=np.sqrt(variance))
    pdf_values /= np.sum(pdf_values)
    return hail_sizes, pdf_values

def monte_carlo_hail_damage(num_years=100000):
    np.random.seed(42)

    solar_panel_file = "output/solar_panel_with_average_hail_frequency.csv"
    hail_damage_file = "被害関数/hail_damage_percentage.csv"
    output_file = "output/simulation_results.csv"
    annual_losses_output_file = "output/annual_losses.csv"

    solar_panel_df = pd.read_csv(solar_panel_file, encoding='utf-8')
    hail_damage_df = pd.read_csv(hail_damage_file, encoding='utf-8')

    solar_panel_df.columns = [
        "mesh_id", "PanelName", "lat", "lon", "Cost", "Mounting", "Module", "Electrical Equipment", "Other", "Average_Hail_Frequency"
    ]

    hail_diameters = hail_damage_df['Hail_Diameter_cm'].values
    damage_percentages = hail_damage_df['Damage_Percentage'].values
    damage_interpolator = interp1d(hail_diameters, damage_percentages, kind='linear', fill_value='extrapolate')

    mean_hail_size = 0.795
    variance_hail_size = 1.61
    x_fit, pdf_values = create_hail_pdf(mean_hail_size, variance_hail_size)

    def sample_hail_sizes(num_samples):
        return np.random.choice(x_fit, size=num_samples, p=pdf_values)

    simulation_results = []
    annual_losses_results = []

    print("シミュレーションを開始...")

    for idx, row in tqdm(solar_panel_df.iterrows(), total=len(solar_panel_df), desc="パネル処理中"):
        panel_name = row['PanelName']
        frequency = row['Average_Hail_Frequency']
        module_cost = row['Module']
        mounting_cost = row['Mounting']
        electrical_cost = row['Electrical Equipment']
        other_cost = row['Other']
        total_cost = module_cost + mounting_cost + electrical_cost + other_cost

        np.random.seed(42 + idx)

        annual_losses = {
            "Module": [],
            "Mounting": [],
            "Electrical Equipment": [],
            "Other": [],
            "Total": []
        }

        for year in tqdm(range(1, num_years + 1), desc=f"{panel_name} シミュレーション中", leave=False):
            num_hail_events = np.random.poisson(frequency)
            if num_hail_events > 0:
                hail_sizes_sampled = sample_hail_sizes(num_hail_events)
                damage_rates = damage_interpolator(hail_sizes_sampled)
                max_damage_rate = np.max(damage_rates) / 100

                # 各項目の被害率
                mounting_damage_rate = max_damage_rate * 0.10
                electrical_damage_rate = max_damage_rate * 0.30
                other_damage_rate = max_damage_rate * 0.30

                # 各項目の被害額
                module_loss = max_damage_rate * module_cost
                mounting_loss = mounting_damage_rate * mounting_cost
                electrical_loss = electrical_damage_rate * electrical_cost
                other_loss = other_damage_rate * other_cost
                total_loss = module_loss + mounting_loss + electrical_loss + other_loss

                annual_losses["Module"].append(module_loss)
                annual_losses["Mounting"].append(mounting_loss)
                annual_losses["Electrical Equipment"].append(electrical_loss)
                annual_losses["Other"].append(other_loss)
                annual_losses["Total"].append(total_loss)

                # 年ごとの被害データを保存
                annual_losses_results.append({
                    "PanelName": panel_name,
                    "Year": year,
                    "Hail Events": num_hail_events,
                    "Hail Sizes": ", ".join(map(str, hail_sizes_sampled)),
                    "Module Loss": module_loss,
                    "Mounting Loss": mounting_loss,
                    "Electrical Equipment Loss": electrical_loss,
                    "Other Loss": other_loss,
                    "Total Loss": total_loss
                })
            else:
                for key in annual_losses:
                    annual_losses[key].append(0)

                annual_losses_results.append({
                    "PanelName": panel_name,
                    "Year": year,
                    "Hail Events": 0,
                    "Hail Sizes": "None",
                    "Module Loss": 0,
                    "Mounting Loss": 0,
                    "Electrical Equipment Loss": 0,
                    "Other Loss": 0,
                    "Total Loss": 0
                })

        # 各確率年ごとの被害額と被害率
        loss_dict = {}
        for period, percentile in zip(["10", "50", "100", "475"], [90, 98, 99, 99.7895]):
            for category in ["Module", "Mounting", "Electrical Equipment", "Other", "Total"]:
                loss_value = np.percentile(annual_losses[category], percentile)
                loss_dict[f"{category} {period}-Year Loss"] = loss_value
                if category == "Total":
                    loss_dict[f"Total {period}-Year Loss %"] = (loss_value / total_cost) * 100 if total_cost else 0
                else:
                    cost = row[category]
                    loss_dict[f"{category} {period}-Year Loss %"] = (loss_value / cost) * 100 if cost else 0

        simulation_results.append({
            'PanelName': panel_name,
            'Module Cost': module_cost,
            'Mounting Cost': mounting_cost,
            'Electrical Equipment Cost': electrical_cost,
            'Other Cost': other_cost,
            'Total Cost': total_cost,
            **loss_dict
        })

    print("シミュレーション完了！データを保存中...")
    simulation_results_df = pd.DataFrame(simulation_results)
    simulation_results_df.to_csv(output_file, index=False, encoding='utf-8-sig')

    annual_losses_df = pd.DataFrame(annual_losses_results)
    annual_losses_df.to_csv(annual_losses_output_file, index=False, encoding='utf-8-sig')

    print("保存完了！")
    return simulation_results_df

results = monte_carlo_hail_damage()

