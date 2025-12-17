"""
Demo/test script for the enhanced display
Shows what the visual display looks like during conversion
"""
import time
import random
from display import get_display

def demo_conversion():
    """Simulate a conversion process to demo the display"""
    print("Starting Enhanced Display Demo...")
    print("This will show you what the display looks like during conversion.")
    print("\nPress Ctrl+C to exit the demo.\n")
    time.sleep(2)

    display = get_display()

    # Setup initial stats
    total_files = 10
    display.update_stats(
        total_files=total_files,
        completed=0,
        failed=0,
        encoder="h264_nvenc (GPU)",
    )

    try:
        # Simulate converting files
        for file_num in range(1, total_files + 1):
            filename = f"video_{file_num:03d}.ts"
            display.update_stats(
                current_file=filename,
                current_progress=0.0,
            )

            # Simulate file conversion with increasing progress
            for progress in range(0, 101, 2):
                display.update_stats(
                    current_progress=float(progress),
                    current_speed=f"{random.uniform(0.8, 1.5):.2f}x",
                    fps=str(random.randint(25, 60)),
                    bitrate=f"{random.randint(800, 2500)} kbits/s",
                )

                # Show the display
                display.display()
                time.sleep(0.1)  # Simulate conversion time

            # Mark file as complete
            if random.random() > 0.1:  # 90% success rate
                display.update_stats(completed=file_num, failed=0)
            else:
                display.update_stats(completed=file_num - 1, failed=1)

        # Final display
        display.display()
        time.sleep(2)

        # Clear and show completion message
        display.clear_screen()
        print("\n✓ Demo completed successfully!")
        print("\nThis is what you'll see when running: python main_enhanced.py")

    except KeyboardInterrupt:
        display.clear_screen()
        print("\nDemo interrupted by user.")


if __name__ == "__main__":
    demo_conversion()
