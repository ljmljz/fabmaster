# fabmaster

Allegro CAD file parser and 3D PCB/components models generator.

This project can parse Allegro CAD fabmaster files and automatically generate:
- PCB UV mapping images
- Component STL models for 3D visualization

## Requirements

- Python 3.6+
- numpy
- numpy-stl
- svgwrite
- Pillow
- pyassimp

## Installation

### From PyPI (recommended)

```bash
pip install fabmaster
```

### From source

```bash
# Clone the repository
git clone https://github.com/fabmaster/fabmaster.git
cd fabmaster

# Install dependencies
pip install -e .
```

### Installing from source with C++ extension (optional)

For better performance with the geometry triangulation, you can build the C++ extension:

```bash
# On Linux/macOS
pip install -e . --config-settings editable_mode=compiling

# Or manually build
python setup.py build_ext --inplace
```

## Usage

### Command Line

```bash
# Parse an Allegro CAD fabmaster file and generate output
fabmaster path/to/your_file.fbm --output ./output_dir
```

### Python API

```python
from fabmaster import FabMaster

# Create a FabMaster instance with your CAD file
fab = FabMaster('path/to/your_file.fbm')

# Parse the file
fab.parse()

# Export all outputs (STL models, UV maps, etc.)
fab.export('./output_directory')
```

### Example

```python
import os
from fabmaster import FabMaster

# Parse Allegro CAD file
cad_file = '28-11353-03_A0_fbm.cad'
fab = FabMaster(cad_file)
fab.parse()

# Export to output directory
output_path = os.path.join(os.path.dirname(cad_file), 'data')
fab.export(output_path)

print("Done! Output files generated in:", output_path)
```

## Output Files

The exporter generates the following files in the output directory:

- `meshes/` - Directory containing STL mesh files
  - `outline.obj` - PCB outline 3D model
  - `packages/*.stl` - Individual component package models
  - `_outline_.jpg` - UV map image
- `svg/` - SVG footprint drawings for each component
- `ComponentConfigs.json` - Component placement and rotation data
- `data.zip` - Compressed archive of all output files

## Development

### Setup development environment

```bash
# Clone and install with dev dependencies
git clone https://github.com/fabmaster/fabmaster.git
cd fabmaster
pip install -e ".[dev]"

# Run tests
pytest

# Run linters
black src/fabmaster/
flake8 src/fabmaster/
mypy src/fabmaster/
```

## License

MIT License

## Author

Jimmy Li (ljzljm@163.com)
