#!/bin/bash
# Fix main.py location - move from src/ to project root

COLLECTORS="bradley_caldwell chala coastal ethical fromm ivyclassic kong orgill talltails"

for collector in $COLLECTORS; do
    echo "Fixing $collector..."
    cd "$collector"
    
    # Move main.py from src/ to root if it exists
    if [ -f "src/main.py" ]; then
        git mv src/main.py main.py
        
        # Update the import path in main.py
        sed -i.bak "s|os.path.join(os.path.dirname(__file__), '../..')|os.path.dirname(__file__)|g" main.py
        rm -f main.py.bak
        
        echo "  ✓ Moved main.py to root and updated imports"
    else
        echo "  - No main.py found in src/"
    fi
    
    cd ..
done

echo "Done!"
