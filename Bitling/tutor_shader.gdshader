shader_type canvas_item;

uniform float depth_strength : hint_range(0.0, 1.0) = 0.5;
uniform bool is_speaking = false;

void fragment() {
    vec4 tex = texture(TEXTURE, UV);
    if (tex.a < 0.1) discard; // Handle transparency
    
    // FAKE 3D DEPTH: Calculate depth based on color brightness
    // Brighter areas are "pushed forward", darker are "pushed back"
    float brightness = (tex.r + tex.g + tex.b) / 3.0;
    
    // Normal calculation for 3D lighting (Simplified)
    float dx = dFdx(brightness);
    float dy = dFdy(brightness);
    vec3 normal = normalize(vec3(-dx, -dy, 1.0 - depth_strength));
    
    // Speaking Ripple Effect
    if (is_speaking) {
        float wave = sin(UV.y * 20.0 + TIME * 10.0) * 0.02;
        tex.rgb += vec3(wave);
    }
    
    // Apply the "Normal" to Godot's 2D lighting system
    NORMAL = normal;
    COLOR = tex;
}
