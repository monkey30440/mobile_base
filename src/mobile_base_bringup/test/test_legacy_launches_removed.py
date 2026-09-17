from pathlib import Path


def test_legacy_mapping_and_navigation_launches_are_removed():
    launch_dir = Path(__file__).resolve().parent.parent / 'launch'

    assert not (launch_dir / 'mapping.launch.py').exists()
    assert not (launch_dir / 'navigation.launch.py').exists()
