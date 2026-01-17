#!/usr/bin/env python3
"""Debug script to test marketplace browse navigation."""

from skill_installer.tui import SkillInstallerApp, DisplaySource, DisplayItem
from skill_installer.registry import RegistryManager

# Initialize with real data
registry_manager = RegistryManager()

# Create and run app
app = SkillInstallerApp(
    registry_manager=registry_manager,
    gitops=None,
    discovery=None,
    installer=None,
)

if __name__ == "__main__":
    app.run()
