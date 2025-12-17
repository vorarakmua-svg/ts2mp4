"""
Interactive configuration wizard for TS2MP4 converter
Helps users set up their configuration interactively
"""
import os
import sys
from pathlib import Path
from colorama import Fore, Style, init as colorama_init


class ConfigurationWizard:
    """Interactive configuration wizard"""

    def __init__(self):
        colorama_init(autoreset=True)
        self.config = {}

    def run(self):
        """Run the interactive configuration wizard"""
        print(f"\n{Fore.CYAN}{Style.BRIGHT}╔{'═' * 78}╗{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{Style.BRIGHT}║{Style.RESET_ALL} {Fore.GREEN}{Style.BRIGHT}TS2MP4 Configuration Wizard{Style.RESET_ALL}" + " " * 51 + f"{Fore.CYAN}{Style.BRIGHT}║{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{Style.BRIGHT}╠{'═' * 78}╣{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{Style.BRIGHT}║{Style.RESET_ALL} This wizard will help you configure TS2MP4 for your system.{' ' * 18}{Fore.CYAN}{Style.BRIGHT}║{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{Style.BRIGHT}║{Style.RESET_ALL} Press Enter to accept default values shown in [brackets].{' ' * 20}{Fore.CYAN}{Style.BRIGHT}║{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{Style.BRIGHT}╚{'═' * 78}╝{Style.RESET_ALL}\n")

        # Directories
        self._configure_directories()

        # FFmpeg paths
        self._configure_ffmpeg()

        # Encoding settings
        self._configure_encoding()

        # Performance settings
        self._configure_performance()

        # Show summary and save
        self._show_summary()
        self._save_configuration()

    def _configure_directories(self):
        """Configure input/output directories"""
        print(f"\n{Fore.YELLOW}{Style.BRIGHT}📁 Directory Configuration{Style.RESET_ALL}")
        print(f"{Fore.CYAN}─{'─' * 77}{Style.RESET_ALL}")

        self.config['input_dir'] = self._prompt(
            "Input directory (where .ts files are located)",
            default=str(Path.home() / "Videos" / "input"),
            validator=self._validate_directory
        )

        self.config['output_dir'] = self._prompt(
            "Output directory (where .mp4 files will be saved)",
            default=str(Path.home() / "Videos" / "output"),
            validator=self._validate_directory
        )

        self.config['log_dir'] = self._prompt(
            "Log directory",
            default="logs",
            validator=self._validate_directory
        )

    def _configure_ffmpeg(self):
        """Configure FFmpeg/FFprobe paths"""
        print(f"\n{Fore.YELLOW}{Style.BRIGHT}🎬 FFmpeg Configuration{Style.RESET_ALL}")
        print(f"{Fore.CYAN}─{'─' * 77}{Style.RESET_ALL}")

        self.config['ffmpeg_bin'] = self._prompt(
            "FFmpeg executable path",
            default="ffmpeg",
            validator=self._validate_command
        )

        self.config['ffprobe_bin'] = self._prompt(
            "FFprobe executable path",
            default="ffprobe",
            validator=self._validate_command
        )

    def _configure_encoding(self):
        """Configure encoding settings"""
        print(f"\n{Fore.YELLOW}{Style.BRIGHT}⚙️  Encoding Configuration{Style.RESET_ALL}")
        print(f"{Fore.CYAN}─{'─' * 77}{Style.RESET_ALL}")

        # GPU settings
        enable_gpu = self._prompt_yes_no(
            "Enable GPU acceleration (NVIDIA only)",
            default="y"
        )
        self.config['enable_gpu'] = "1" if enable_gpu else "0"

        if enable_gpu:
            force_gpu = self._prompt_yes_no(
                "Force GPU mode (fail if GPU unavailable)",
                default="n"
            )
            self.config['force_gpu'] = "1" if force_gpu else "0"

            preset = self._prompt_choice(
                "NVENC preset",
                choices=['p1', 'p2', 'p3', 'p4', 'p5', 'p6', 'p7'],
                default='p4',
                descriptions={
                    'p1': 'Fastest (lower quality)',
                    'p4': 'Balanced (recommended)',
                    'p7': 'Slowest (best quality)'
                }
            )
            self.config['preset'] = preset

        # Quality settings
        print(f"\n{Fore.CYAN}Quality (CRF): Lower values = better quality, larger files{Style.RESET_ALL}")
        print(f"{Fore.CYAN}  • 18-20: Very high quality{Style.RESET_ALL}")
        print(f"{Fore.CYAN}  • 21-23: High quality (recommended){Style.RESET_ALL}")
        print(f"{Fore.CYAN}  • 24-28: Medium quality{Style.RESET_ALL}")

        crf = self._prompt(
            "CRF value (0-51)",
            default="21",
            validator=lambda x: self._validate_range(x, 0, 51)
        )
        self.config['crf_value'] = crf

    def _configure_performance(self):
        """Configure performance settings"""
        print(f"\n{Fore.YELLOW}{Style.BRIGHT}⚡ Performance Configuration{Style.RESET_ALL}")
        print(f"{Fore.CYAN}─{'─' * 77}{Style.RESET_ALL}")

        print(f"\n{Fore.CYAN}Concurrent conversions: More = faster, but uses more resources{Style.RESET_ALL}")
        print(f"{Fore.CYAN}  • 1: Sequential (safest, lowest resource usage){Style.RESET_ALL}")
        print(f"{Fore.CYAN}  • 2-4: Moderate parallelism (recommended){Style.RESET_ALL}")
        print(f"{Fore.CYAN}  • 5+: High parallelism (powerful systems only){Style.RESET_ALL}")

        max_concurrent = self._prompt(
            "Maximum concurrent conversions",
            default="1",
            validator=lambda x: self._validate_range(x, 1, 16)
        )
        self.config['max_concurrent'] = max_concurrent

        sleep_between = self._prompt(
            "Sleep between conversions (seconds)",
            default="2",
            validator=lambda x: self._validate_range(x, 0, 60)
        )
        self.config['sleep_between'] = sleep_between

    def _show_summary(self):
        """Show configuration summary"""
        print(f"\n{Fore.GREEN}{Style.BRIGHT}📋 Configuration Summary{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'═' * 78}{Style.RESET_ALL}")

        print(f"\n{Fore.YELLOW}Directories:{Style.RESET_ALL}")
        print(f"  Input:  {self.config['input_dir']}")
        print(f"  Output: {self.config['output_dir']}")
        print(f"  Logs:   {self.config['log_dir']}")

        print(f"\n{Fore.YELLOW}FFmpeg:{Style.RESET_ALL}")
        print(f"  FFmpeg:  {self.config['ffmpeg_bin']}")
        print(f"  FFprobe: {self.config['ffprobe_bin']}")

        print(f"\n{Fore.YELLOW}Encoding:{Style.RESET_ALL}")
        print(f"  GPU Enabled:   {self.config['enable_gpu'] == '1'}")
        if 'force_gpu' in self.config:
            print(f"  Force GPU:     {self.config['force_gpu'] == '1'}")
        if 'preset' in self.config:
            print(f"  NVENC Preset:  {self.config.get('preset', 'N/A')}")
        print(f"  CRF Value:     {self.config['crf_value']}")

        print(f"\n{Fore.YELLOW}Performance:{Style.RESET_ALL}")
        print(f"  Max Concurrent: {self.config['max_concurrent']}")
        print(f"  Sleep Between:  {self.config['sleep_between']}s")

        print(f"\n{Fore.CYAN}{'═' * 78}{Style.RESET_ALL}")

    def _save_configuration(self):
        """Save configuration to .env file"""
        if not self._prompt_yes_no("\nSave this configuration", default="y"):
            print(f"\n{Fore.YELLOW}Configuration not saved.{Style.RESET_ALL}")
            return

        env_file = Path.cwd() / ".env"

        # Create .env content
        lines = [
            "# TS2MP4 Configuration",
            "# Generated by Configuration Wizard",
            "",
            "# Directories",
            f"TS2MP4_INPUT_DIR={self.config['input_dir']}",
            f"TS2MP4_OUTPUT_DIR={self.config['output_dir']}",
            f"TS2MP4_LOG_DIR={self.config['log_dir']}",
            "",
            "# FFmpeg",
            f"TS2MP4_FFMPEG_BIN={self.config['ffmpeg_bin']}",
            f"TS2MP4_FFPROBE_BIN={self.config['ffprobe_bin']}",
            "",
            "# Encoding",
            f"TS2MP4_ENABLE_GPU={self.config['enable_gpu']}",
        ]

        if 'force_gpu' in self.config:
            lines.append(f"TS2MP4_FORCE_GPU={self.config['force_gpu']}")

        if 'preset' in self.config:
            lines.append(f"TS2MP4_NVENC_PRESET={self.config['preset']}")

        lines.extend([
            f"TS2MP4_CRF_VALUE={self.config['crf_value']}",
            "",
            "# Performance",
            f"TS2MP4_MAX_CONCURRENT={self.config['max_concurrent']}",
            f"TS2MP4_SLEEP_BETWEEN={self.config['sleep_between']}",
            ""
        ])

        env_file.write_text('\n'.join(lines))

        print(f"\n{Fore.GREEN}✓ Configuration saved to: {env_file}{Style.RESET_ALL}")
        print(f"\n{Fore.CYAN}To use this configuration:{Style.RESET_ALL}")
        print(f"  1. The .env file will be automatically loaded")
        print(f"  2. Or set these as environment variables")
        print(f"  3. Or use command-line arguments to override")

        # Create directories
        if self._prompt_yes_no("\nCreate directories now", default="y"):
            for key in ['input_dir', 'output_dir', 'log_dir']:
                dir_path = Path(self.config[key])
                dir_path.mkdir(parents=True, exist_ok=True)
                print(f"  ✓ Created: {dir_path}")

    def _prompt(self, question, default="", validator=None):
        """Prompt user for input with validation"""
        while True:
            prompt_text = f"{Fore.CYAN}? {question}"
            if default:
                prompt_text += f" {Fore.GREEN}[{default}]{Style.RESET_ALL}"
            prompt_text += f": {Style.RESET_ALL}"

            response = input(prompt_text).strip()
            value = response if response else default

            if validator:
                valid, message = validator(value)
                if not valid:
                    print(f"{Fore.RED}✗ {message}{Style.RESET_ALL}")
                    continue

            return value

    def _prompt_yes_no(self, question, default="y"):
        """Prompt for yes/no answer"""
        while True:
            default_text = "Y/n" if default.lower() == "y" else "y/N"
            prompt_text = f"{Fore.CYAN}? {question} {Fore.GREEN}[{default_text}]{Style.RESET_ALL}: "
            response = input(prompt_text).strip().lower()

            if not response:
                response = default.lower()

            if response in ['y', 'yes']:
                return True
            elif response in ['n', 'no']:
                return False
            else:
                print(f"{Fore.RED}✗ Please answer 'y' or 'n'{Style.RESET_ALL}")

    def _prompt_choice(self, question, choices, default, descriptions=None):
        """Prompt user to choose from options"""
        print(f"\n{Fore.CYAN}? {question}{Style.RESET_ALL}")
        for choice in choices:
            desc = descriptions.get(choice, "") if descriptions else ""
            marker = "→" if choice == default else " "
            print(f"  {Fore.GREEN}{marker} {choice}{Style.RESET_ALL}  {desc}")

        while True:
            response = input(f"{Fore.CYAN}  Choice {Fore.GREEN}[{default}]{Style.RESET_ALL}: ").strip()
            value = response if response else default

            if value in choices:
                return value
            else:
                print(f"{Fore.RED}✗ Invalid choice. Please select from: {', '.join(choices)}{Style.RESET_ALL}")

    def _validate_directory(self, path):
        """Validate directory path"""
        if not path:
            return False, "Directory path cannot be empty"
        return True, ""

    def _validate_command(self, command):
        """Validate command exists"""
        if not command:
            return False, "Command cannot be empty"
        return True, ""

    def _validate_range(self, value, min_val, max_val):
        """Validate numeric range"""
        try:
            num = float(value)
            if num < min_val or num > max_val:
                return False, f"Value must be between {min_val} and {max_val}"
            return True, ""
        except ValueError:
            return False, "Value must be a number"


def main():
    """Run configuration wizard"""
    wizard = ConfigurationWizard()
    try:
        wizard.run()
        print(f"\n{Fore.GREEN}{Style.BRIGHT}✓ Configuration wizard complete!{Style.RESET_ALL}\n")
    except KeyboardInterrupt:
        print(f"\n\n{Fore.YELLOW}Configuration wizard cancelled.{Style.RESET_ALL}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
