// --- PARAMETERS ---
$fn = 100;

// Pot Dimensions (Oval)
pot_width = 150;
pot_length = 180;
pot_height = 200;
wall_thick = 4;

// Catalyst Dimensions
cat_diam = 60;
cat_height = 100;

// --- MODULES ---

module oval_shape(w, l) {
    scale([1, l/w, 1]) circle(d=w);
}

module pressure_vessel() {
    color("Silver", 0.6)
    difference() {
        linear_extrude(pot_height)
            oval_shape(pot_width + wall_thick*2, pot_length + wall_thick*2);
        translate([0,0, wall_thick])
        linear_extrude(pot_height + 1)
            oval_shape(pot_width, pot_length);
    }
}

module internal_coil_liner() {
    // The "Bucket" that holds the waste and induction coils
    // Ceramic material (White)
    liner_w = pot_width - 5;
    liner_l = pot_length - 5;
    liner_h = pot_height - 60;

    translate([0,0, wall_thick + 5])
    union() {
        color("White", 0.4)
        difference() {
            linear_extrude(liner_h)
                oval_shape(liner_w, liner_l);
            translate([0,0, 10])
            linear_extrude(liner_h)
                oval_shape(liner_w - 20, liner_l - 20);
        }
        // Copper Coils Embedded in Wall
        color("Orange")
        for(i = [0:6]) {
            translate([0,0, 20 + i*25])
            linear_extrude(5)
            difference() {
                oval_shape(liner_w - 5, liner_l - 5);
                oval_shape(liner_w - 15, liner_l - 15);
            }
        }
    }
}

module smart_lid_assembly() {
    // Positioned at top of pot
    translate([0,0, pot_height - 10]) {

        // 1. The Oval Lid Plate
        color("DimGray")
        linear_extrude(8)
            oval_shape(pot_width + 8, pot_length + 8);

        // 2. The High-Temp Silicone Gasket (Red)
        color("Red")
        translate([0,0,8])
        linear_extrude(4)
            difference() {
                oval_shape(pot_width + 8, pot_length + 8);
                oval_shape(pot_width - 10, pot_length - 10);
            }

        // 3. The "Reaction Tower" (Manifold)
        translate([0,0, 12]) {

            // A. The Steam Pipe (Vertical)
            color("Silver")
            cylinder(h=40, d=20);

            // B. The Solenoid Valve Block
            translate([-15, -15, 40])
            color("Blue") cube([30,30,30]); // Valve Body

            // C. The Catalyst Chamber (Sitting above valve)
            translate([0,0,70]) {
                color("DarkSlateGray")
                difference() {
                    cylinder(h=cat_height, d=cat_diam); // Main Housing
                    translate([0,0,-1]) cylinder(h=cat_height+2, d=cat_diam-10); // Hollow
                }

                // Catalyst Pellets (Representation)
                color("Black")
                translate([0,0,10]) cylinder(h=cat_height-20, d=cat_diam-15);

                // Cartridge Heater (Center Rod)
                color("Gold")
                cylinder(h=cat_height + 20, d=8);

                // Text Label
                color("White")
                translate([0, -cat_diam/2 - 10, cat_height/2])
                rotate([90,0,0])
                text("Magnetite Cat.", size=8, halign="center");
            }

            // D. Electrical Feedthrough (For Induction Coil Power)
            translate([40, 0, 0]) {
                color("Goldenrod") cylinder(h=30, d=15); // Ceramic Feedthrough
                color("Black") translate([0,0,30]) cylinder(h=20, d=5); // Cable
            }
        }
    }
}

// --- ASSEMBLY ---
difference() {
    union() {
        pressure_vessel();
        internal_coil_liner();
        smart_lid_assembly();
    }
    // Cutaway to see inside
    translate([0, -200, -10]) cube([200, 200, 400]);
}
