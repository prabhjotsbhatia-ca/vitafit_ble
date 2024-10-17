import asyncio,os, logging
from vitafit_vt701_ble import (
    IMPEDANCE_KEY,
    WEIGHT_KEY,
    VitafitBodyFatScale,
    ScaleData,
    WeightUnit,
    BodyMetrics,
    Sex,
)


# Get the directory of the current script
current_dir = os.path.dirname(os.path.abspath(__file__))

# Construct the relative path for the log file
log_file = os.path.join(current_dir, '../', 'basic_test.log')
print(f"Writing to log file: {log_file}")

# Configure logging
logging.basicConfig(filename=log_file,
                    filemode='a',
                    force=True,
                    level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')
logger = logging.getLogger(__name__)

async def main():
    def notification_callback(data: ScaleData):
        print(f"Weight: {data.measurements[WEIGHT_KEY]} kg")
        print(f"Display Unit: {data.display_unit.name}")
        if IMPEDANCE_KEY in data.measurements:
            print(f"Impedance: {data.measurements[IMPEDANCE_KEY]} Ω")

            # Calculate body metrics
            # Note: Replace with your actual height, age and sex
            body_metrics = BodyMetrics(
                weight_kg=data.measurements[WEIGHT_KEY],
                height_m=1.75,  # Example height
                age=30,  # Example age
                sex=Sex.Male,  # Example sex
                impedance=data.measurements[IMPEDANCE_KEY]
            )
            print(f"Body Mass Index: {body_metrics.body_mass_index:.2f}")
            print(f"Body Fat Percentage: {
                  body_metrics.body_fat_percentage:.1f}%")
            print(f"Fat-Free Weight: {body_metrics.fat_free_weight:.2f} kg")
            print(f"Subcutaneous Fat Percentage: {
                  body_metrics.subcutaneous_fat_percentage:.1f}%")
            print(f"Visceral Fat Value: {body_metrics.visceral_fat_value}")
            print(f"Body Water Percentage: {
                  body_metrics.body_water_percentage:.1f}%")
            print(f"Basal Metabolic Rate: {
                  body_metrics.basal_metabolic_rate} calories")
            print(f"Skeletal Muscle Percentage: {
                  body_metrics.skeletal_muscle_percentage:.1f}%")
            print(f"Muscle Mass: {body_metrics.muscle_mass:.2f} kg")
            print(f"Bone Mass: {body_metrics.bone_mass:.2f} kg")
            print(f"Protein Percentage: {
                  body_metrics.protein_percentage:.1f}%")
            print(f"Metabolic Age: {body_metrics.metabolic_age} years")

    # Replace XX:XX:XX:XX:XX:XX with your scale's Bluetooth address
    scale = VitafitBodyFatScale("F8:8F:C8:14:AA:60", notification_callback)
    scale.display_unit = WeightUnit.KG  # Set display unit to kilograms

    await scale.async_start()
    await asyncio.sleep(30)  # Wait for measurements
    await scale.async_stop()

asyncio.run(main())
