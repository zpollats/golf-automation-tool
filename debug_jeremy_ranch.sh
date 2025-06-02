#!/bin/bash
# debug_jeremy_ranch.sh
# Commands to debug Jeremy Ranch tee time slot detection

echo "🏌️ Jeremy Ranch Golf Club - Time Slot Debugger"
echo "================================================"

# Make sure the container is running
echo "📋 Starting containers..."
docker-compose up -d

# Wait for containers to be ready
echo "⏳ Waiting for containers to start..."
sleep 10

echo ""
echo "🔍 Available Debug Commands:"
echo ""
echo "1. Full Debug Analysis (Recommended first run)"
echo "   docker-compose exec golf-booking-app python -c \"from src.debug_time_slots import debug_time_slots; debug_time_slots()\""
echo ""
echo "2. Quick Element Check"
echo "   docker-compose exec golf-booking-app python -c \"from src.debug_time_slots import quick_element_check; quick_element_check()\""
echo ""
echo "3. Debug Specific Date (replace 7 with number of days ahead)"
echo "   docker-compose exec golf-booking-app python -c \"from src.debug_time_slots import debug_specific_date; debug_specific_date(7)\""
echo ""
echo "4. View Container Logs"
echo "   docker-compose logs -f golf-booking-app"
echo ""
echo "5. Access VNC Viewer (while debug is running)"
echo "   Open browser: http://localhost:7900"
echo "   Password: secret"
echo ""

# Function to run full debug
run_full_debug() {
    echo "🚀 Running Full Debug Analysis..."
    echo "This will:"
    echo "  - Login to Jeremy Ranch"
    echo "  - Navigate to tee time booking"
    echo "  - Set date to 7 days from now"
    echo "  - Analyze all page elements"
    echo "  - Extract HTML samples"
    echo "  - Save results to /tmp/ files"
    echo "  - Keep browser open for 60 seconds"
    echo ""
    echo "🔍 You can view the browser at http://localhost:7900 (password: secret)"
    echo ""
    
    docker-compose exec golf-booking-app python -c "
from src.debug_time_slots import debug_time_slots
debug_time_slots()
"
}

# Function to run quick check
run_quick_check() {
    echo "⚡ Running Quick Element Check..."
    docker-compose exec golf-booking-app python -c "
from src.debug_time_slots import quick_element_check
quick_element_check()
"
}

# Function to copy debug files from container
copy_debug_files() {
    echo "📁 Copying debug files from container..."
    
    # Create local debug directory
    mkdir -p ./debug_results
    
    # Copy files from container
    docker-compose exec golf-booking-app ls /tmp/jeremy_ranch_* 2>/dev/null | while read file; do
        if [ ! -z "$file" ]; then
            filename=$(basename "$file")
            echo "Copying $filename..."
            docker-compose exec golf-booking-app cat "$file" > "./debug_results/$filename"
        fi
    done
    
    echo "✅ Debug files copied to ./debug_results/"
}

# Function to analyze debug results
analyze_results() {
    echo "📊 Analyzing Debug Results..."
    
    if [ -d "./debug_results" ]; then
        echo "Found debug files:"
        ls -la ./debug_results/
        
        echo ""
        echo "🔍 Quick Analysis:"
        
        # Look for JSON analysis files
        for file in ./debug_results/jeremy_ranch_analysis_*.json; do
            if [ -f "$file" ]; then
                echo "Analysis from $file:"
                cat "$file" | grep -E '"Elements with|found"' | head -10
            fi
        done
        
        # Look for HTML files
        for file in ./debug_results/jeremy_ranch_page_*.html; do
            if [ -f "$file" ]; then
                echo ""
                echo "HTML Analysis from $file:"
                echo "File size: $(wc -c < "$file") bytes"
                
                # Count potential time elements
                echo "Potential time elements found:"
                grep -c "AM\|PM" "$file" 2>/dev/null | head -1
                grep -c "available\|book\|time" "$file" 2>/dev/null | head -1
            fi
        done
    else
        echo "❌ No debug results found. Run the debug commands first."
    fi
}

# Main menu
case "$1" in
    "full")
        run_full_debug
        ;;
    "quick")
        run_quick_check
        ;;
    "copy")
        copy_debug_files
        ;;
    "analyze")
        analyze_results
        ;;
    "logs")
        docker-compose logs -f golf-booking-app
        ;;
    *)
        echo ""
        echo "🎯 Usage: $0 {full|quick|copy|analyze|logs}"
        echo ""
        echo "Commands:"
        echo "  full     - Run complete debug analysis"
        echo "  quick    - Run quick element check"
        echo "  copy     - Copy debug files from container"
        echo "  analyze  - Analyze copied debug results"
        echo "  logs     - View application logs"
        echo ""
        echo "Recommended workflow:"
        echo "1. $0 full     # Run full debug"
        echo "2. $0 copy     # Copy results locally"
        echo "3. $0 analyze  # Analyze results"
        echo ""
        echo "🌐 VNC Access: http://localhost:7900 (password: secret)"
        ;;
esac