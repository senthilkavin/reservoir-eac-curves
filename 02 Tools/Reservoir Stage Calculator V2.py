from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtWidgets import QInputDialog, QMessageBox
from qgis.core import QgsProject, QgsField, QgsVectorLayer, QgsMapLayer, QgsCoordinateReferenceSystem
from qgis.utils import iface
import processing

# --- Core Functions ---

# Function to create an interactive dropdown for selecting a DEM layer
def select_dem_layer():
    selected_layer = iface.activeLayer()
    # Filter for only Raster layers
    layers = [layer for layer in QgsProject.instance().mapLayers().values() if layer.type() == QgsMapLayer.RasterLayer]
    if not layers:
        raise Exception("No raster layers found in the project. Please load a DEM.")

    layer_names = [layer.name() for layer in layers]
    # Set default to active layer if it's a raster, otherwise the first raster layer
    default_layer = selected_layer.name() if selected_layer and selected_layer.type() == QgsMapLayer.RasterLayer else layer_names[0]
    
    selected, ok = QInputDialog.getItem(iface.mainWindow(), "Select DEM Layer", "Choose a DEM:", layer_names, layer_names.index(default_layer), False)
    if not ok:
        raise Exception("DEM selection canceled by user.")
        
    dem_layer = next(layer for layer in layers if layer.name() == selected)
    
    # Check 1: Is the CRS defined?
    crs = dem_layer.crs()
    if not crs.isValid():
        raise Exception(f"The DEM layer '{dem_layer.name()}' has **NO Coordinate Reference System (CRS) defined**. You must set a Projected CRS (e.g., UTM) for accurate area and volume calculations.")

    # Check 2: Is the defined CRS Projected?
    if crs.isGeographic():
        # Raise an exception if the CRS is geographic (like WGS 84, Lat/Lon)
        raise Exception(f"The DEM layer '{dem_layer.name()}' uses a **Geographic CRS** ({crs.description()}). Area and volume calculations require a **Projected CRS** (e.g., UTM) with units in meters.")
        
    return dem_layer

# Function to calculate min and max elevation of a raster layer
def calculate_elevation_range(raster_layer):
    stats = raster_layer.dataProvider().bandStatistics(1)
    # Check if stats are available
    if stats.minimumValue is None or stats.maximumValue is None:
         raise Exception("Could not calculate elevation statistics for the DEM. Check if the raster layer is valid.")
    return stats.minimumValue, stats.maximumValue

# Function to get numeric input from the user
def get_numeric_input(prompt, default_value):
    # Use QInputDialog.getDouble for float/double input
    value, ok = QInputDialog.getDouble(iface.mainWindow(), "Input Value", prompt, default_value, decimals=4)
    if not ok:
        raise Exception(f"{prompt} input canceled by user.")
    return value

# --- Main Execution Block with Error Handling ---
try:
    # Select the DEM layer and check CRS
    dem_layer = select_dem_layer()
    
    # Calculate and propose elevation range
    min_calculated, max_calculated = calculate_elevation_range(dem_layer)
    
    # Get user inputs for minimum, maximum, and increment values
    min_elevation = get_numeric_input(f"Enter minimum elevation (suggested: {min_calculated:.2f}):", min_calculated)
    max_elevation = get_numeric_input(f"Enter maximum elevation (suggested: {max_calculated:.2f}):", max_calculated)
    increment = get_numeric_input("Enter increment value:", 1)

    # Basic input validation
    if min_elevation >= max_elevation:
        raise Exception("Minimum elevation must be less than the maximum elevation.")
    if increment <= 0:
        raise Exception("Increment value must be positive.")

    # Generate the list of levels
    levels = [min_elevation + i * increment for i in range(int((max_elevation - min_elevation) / increment) + 1)]
    if not levels:
         raise Exception("No elevation levels could be generated. Check your min/max/increment settings.")
         
    # Temporary storage for layers
    merged_layer_path = 'memory:'
    dbf_list = []
    
    # Loop over the elevation range
    iface.mainWindow().statusBar().showMessage(f"Processing {len(levels)} elevation levels...")
    for i, level in enumerate(levels):
        iface.mainWindow().statusBar().showMessage(f"Processing level {i+1} of {len(levels)}: {level:.2f} m...")
        
        # Run the raster surface volume tool for each level
        result = processing.run(
            "native:rastersurfacevolume",
            {
                'INPUT': dem_layer,
                'BAND': 1,
                'LEVEL': level,
                'METHOD': 1, # 1 for Above Base Level
                'OUTPUT_HTML_FILE': 'TEMPORARY_OUTPUT',
                'OUTPUT_TABLE': 'memory:'
            }
        )
        volume_layer = result['OUTPUT_TABLE']
        
        # Add new fields in the desired order
        volume_layer.dataProvider().addAttributes([
            QgsField("BaseLevel_M", QVariant.Double),
            QgsField("Pixels", QVariant.Int),
            QgsField("Area_m2", QVariant.Double), 
            QgsField("Capacity_M3", QVariant.Double),
            QgsField("Area_ha", QVariant.Double),
            QgsField("Area_km2", QVariant.Double),
            QgsField("Capacity_MM3", QVariant.Double),
            QgsField("Area_acre", QVariant.Double),
            QgsField("Capacity_acre_ft", QVariant.Double) 
        ])
        volume_layer.updateFields()
        
        # Update the layer with the new fields
        volume_layer.startEditing()
        for f in volume_layer.getFeatures():
            # Ensure that we don't have None values for the fields
            volume_abs = abs(f["Volume"]) if f["Volume"] is not None else 0
            volume_million_m3 = volume_abs / 1e6
            area_m2 = abs(f["m2"]) if f["m2"] is not None else 0
            area_ha = area_m2 / 1e4
            area_km2 = area_m2 / 1e6
            pixel_count = abs(f["pixel_count"]) if "pixel_count" in f.fields().names() and f["pixel_count"] is not None else 0
            # Calculate Acres from Area_m2
            acres = area_m2 / 4046.8564224
            
            # Use Volume_abs for capacity calculations for simplicity/consistency
            capacity_m3 = volume_abs
            # Calculate Capacity_acre_ft for the current feature as absolute value
            capacity_acre_ft = abs(capacity_m3 / 1233.4818375475) if capacity_m3 != 0 else 0 

            # Assign calculated values to the fields
            f["BaseLevel_M"] = level
            f["Pixels"] = pixel_count
            f["Area_m2"] = area_m2
            f["Capacity_M3"] = volume_abs
            f["Area_ha"] = area_ha
            f["Area_km2"] = area_km2
            f["Capacity_MM3"] = volume_million_m3
            f["Area_acre"] = acres
            f["Capacity_acre_ft"] = capacity_acre_ft 
            volume_layer.updateFeature(f)
        volume_layer.commitChanges()
        dbf_list.append(volume_layer)

    if not dbf_list:
        raise Exception("No results were generated during the processing loop.")
        
    # Merge all layers into one
    iface.mainWindow().statusBar().showMessage("Merging results...")
    merged_result = processing.run("native:mergevectorlayers", {
        'LAYERS': dbf_list,
        'CRS': None,
        'OUTPUT': merged_layer_path
    })
    merged_layer = merged_result['OUTPUT']
    
    # Remove unwanted fields (unchanged)
    layer_fields = merged_layer.dataProvider().fields()
    fields_to_remove = [field.name() for field in layer_fields if field.name().lower() in ["layer", "path", "volume", "m2", "pixel_count"]]
    
    # Ensure indices are valid before attempting to delete
    indices_to_remove = [layer_fields.indexOf(field_name) for field_name in fields_to_remove if layer_fields.indexOf(field_name) >= 0]
    merged_layer.dataProvider().deleteAttributes(indices_to_remove)
    merged_layer.updateFields()
    
    # Rename the columns (unchanged)
    data_provider = merged_layer.dataProvider()
    rename_map = {
        "BaseLevel_M": "BaseLevel_m", 
        "Capacity_M3": "Capacity_m3", 
        "Capacity_MM3": "Capacity_MCM", 
        "Area_acre": "Area_acre", 
        "Capacity_acre_ft": "Capacity_acre_ft" 
    }
    
    rename_actions = {}
    for old_name, new_name in rename_map.items():
        index = data_provider.fieldNameIndex(old_name)
        if index >= 0:
            rename_actions[index] = new_name
            
    if rename_actions:
        data_provider.renameAttributes(rename_actions)
        merged_layer.updateFields()

    # Add the merged layer to the project
    dem_layer_name = dem_layer.name()
    merged_layer.setName(f"Elevation_Area_Volume_{dem_layer_name}")
    QgsProject.instance().addMapLayer(merged_layer)
    
    # Final success message
    iface.mainWindow().statusBar().showMessage('Calculations Completed Successfully!')
    QMessageBox.information(iface.mainWindow(), "Success", f"Area-Volume calculations for '{dem_layer_name}' are complete. The results are in the layer: '{merged_layer.name()}'")

except Exception as e:
    # Display a critical error message box on failure
    error_message = f"**Script Error!**\n\n**Reason:** {str(e)}"
    QMessageBox.critical(iface.mainWindow(), "Volume Calculation Failed", error_message)
    # Clear status bar on error
    iface.mainWindow().statusBar().clearMessage()

finally:
    # Ensure the status bar is cleared even if no error occurred in the except block
    if 'iface' in locals():
         iface.mainWindow().statusBar().clearMessage()