# Models Directory & System Under Test (SUT)

This directory contains model definitions, configuration metadata, and original demonstration models for the SimuVerify framework.

---

## 1. System Under Test: DC Motor Speed Controller

The demonstration model is an electromechanical **Direct Current (DC) Motor Speed Control System** with closed-loop PID regulation and external disturbance load injection.

### Physical Equations of Motion

1. **Armature Electrical Circuit (Kirchhoff's Voltage Law)**:
   $$V(t) = R \cdot i(t) + L \frac{di(t)}{dt} + K_e \cdot \omega(t)$$

2. **Rotor Mechanical Dynamics (Newton's Second Law for Rotation)**:
   $$J \frac{d\omega(t)}{dt} + B \cdot \omega(t) = K_t \cdot i(t) - \tau_{\text{load}}(t)$$

### Motor Physical Constants

| Parameter | Symbol | Value | Unit | Description |
| :--- | :--- | :--- | :--- | :--- |
| Armature Resistance | $R$ | $0.5$ | $\Omega$ | Winding electrical resistance |
| Armature Inductance | $L$ | $0.02$ | $\text{H}$ | Winding self-inductance |
| Torque Constant | $K_t$ | $0.1$ | $\text{N}\cdot\text{m}/\text{A}$ | Current-to-torque proportionality |
| Back-EMF Constant | $K_e$ | $0.1$ | $\text{V}/(\text{rad}/\text{s})$ | Rotor velocity counter-voltage |
| Rotor Inertia | $J$ | $0.01$ | $\text{kg}\cdot\text{m}^2$ | Moment of inertia of motor shaft |
| Viscous Damping | $B$ | $0.005$ | $\text{N}\cdot\text{m}\cdot\text{s}/\text{rad}$ | Friction loss on shaft bearings |
| Maximum Supply Voltage | $V_{\text{max}}$ | $24.0$ | $\text{V}$ | Power amplifier / H-bridge rail limit |
| Current Protection Limit | $I_{\text{max}}$ | $12.0$ | $\text{A}$ | Motor drive thermal current limit |

---

## 2. Generating the Simulink Block Diagram (`.slx`)

To generate the original Simulink model file programmatically:

1. Open MATLAB.
2. In the MATLAB Command Window, execute:
   ```matlab
   addpath(genpath('matlab'));
   build_simulink_model;
   ```
3. This creates `models/dc_motor_control.slx` using native Simulink APIs (`new_system`, `add_block`, `add_line`, `save_system`).
4. You can then open and visually inspect the model by typing:
   ```matlab
   open_system('models/dc_motor_control.slx');
   ```

---

## 3. Execution Without Simulink

When Simulink is not installed or licensed on the target workstation or CI server:
- **MATLAB**: The runner automatically uses `matlab/sim/dc_motor_model.m`, solving the exact differential equations via 4th-Order Runge-Kutta numerical integration.
- **Python / CI**: The runner uses `simuverify/engine/simulator.py`, providing 100% deterministic mathematical equivalence in headless CI runners without third-party toolboxes.
- **Integrity Guarantee**: The validation reports explicitly label the execution mode and never fabricate or claim a Simulink run occurred when the fallback solver was used.
