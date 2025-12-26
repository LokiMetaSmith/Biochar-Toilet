// --- PARAMETERS ---
$fn = 100;

// Pot Dimensions (Oval Shape)
pot_width = 150;    // Minor Axis
pot_length = 180;   // Major Axis (Oval)
pot_height = 200;
wall_thick = 5;

// Coil Liner Dimensions
liner_thick = 15;   // Thick ceramic to protect coils
coil_turns = 8;
coil_radius = 4;    // Thickness of the copper wire

// --- MODULES ---

module oval_shape(w, l) {
    scale([1, l/w, 1]) circle(d=w);
}

module pressure_vessel() {
    color("Silver", 0.5)
    difference() {
        // Outer Shell
        linear_extrude(pot_height)
            oval_shape(pot_width + wall_thick*2, pot_length + wall_thick*2);

        // Inner Cavity (Hollow)
        translate([0,0, wall_thick])
        linear_extrude(pot_height + 1)
            oval_shape(pot_width, pot_length);
    }
}

module oval_lid() {
    // The lid is slightly larger than the opening (to seal from inside)
    lid_w = pot_width + 10;
    lid_l = pot_length + 10;

    color("DimGray")
    translate([0,0, pot_height - 30]) // Positioned "inside" near top
    union() {
        // Main Lid Body
        linear_extrude(10)
            oval_shape(lid_w, lid_l);

        // The Gasket (Soft Silicone)
        color("Red")
        translate([0,0,10])
        linear_extrude(5)
            difference() {
                oval_shape(lid_w, lid_l);
                oval_shape(lid_w - 20, lid_l - 20);
            }

        // Handle / Hinge Mount
        translate([0,0,-15])
            cylinder(h=15, d=20);
    }
}

module internal_coil_liner() {
    // This represents the Ceramic/Epoxy casting that holds the coils
    // It sits INSIDE the pressure vessel

    liner_w = pot_width - 2; // Clearance fit
    liner_l = pot_length - 2;
    liner_h = pot_height - 60; // Leave room for lid

    translate([0,0, wall_thick])
    union() {
        // 1. The Ceramic Cup Material (Translucent to see coils)
        color("White", 0.3)
        difference() {
            linear_extrude(liner_h)
                oval_shape(liner_w, liner_l);

            translate([0,0, liner_thick])
            linear_extrude(liner_h)
                oval_shape(liner_w - liner_thick*2, liner_l - liner_thick*2);
        }

        // 2. The Induction Coils (Embedded inside the wall)
        color("Orange")
        translate([0,0, liner_thick])
        for(i = [0 : coil_turns-1]) {
            translate([0,0, i * (liner_h/coil_turns) * 0.8])
            difference() {
                // Create a ring
                linear_extrude(coil_radius*2)
                    difference() {
                         oval_shape(liner_w - liner_thick, liner_l - liner_thick);
                         oval_shape(liner_w - liner_thick - coil_radius*2, liner_l - liner_thick - coil_radius*2);
                    }
            }
        }
    }
}

// --- RENDER ASSEMBLY ---

// 1. The Stainless Steel Pressure Vessel
pressure_vessel();

// 2. The Internal "Potted" Coil Assembly
// (This protects coils from the waste and prevents eddy currents in the pot)
internal_coil_liner();

// 3. The Inside-Fitting Oval Lid
// (Rotated to show how it fits, then pulls up to seal)
rotate([0,0,0]) oval_lid();

// Cutaway Cube (Uncomment to see inside)
/*
color("Red", 0.1)
translate([0,-100,-10]) cube([200,200,300]);
*/
