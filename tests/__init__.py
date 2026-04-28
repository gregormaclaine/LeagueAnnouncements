# Run the suite from the project root to avoid package name collisions with src/:
#   python3.12 -m unittest discover -s . -p "test_*.py" -v
#
# Each test module is responsible for inserting src/ into sys.path and
# stubbing external dependencies (e.g. logs) before importing project code.
