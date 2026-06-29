module ZIHsim


using ModelingToolkit
using ModelingToolkit: t_nounits as t, D_nounits as D
using DifferentialEquations
using DataInterpolations
using DataFrames
using Dates
using OrdinaryDiffEqBDF
using SymbolicIndexingInterface
using SciMLStructures: Tunable, canonicalize, replace
using PreallocationTools
using PrecompileTools: @setup_workload, @compile_workload


# Components

@connector function HeatPort(; name)
    pars = @parameters begin
    end

    vars = @variables begin
        T(t), [guess = 300, description = "Temperature in K"]
        Q̇(t), [guess = 0, connect = Flow, description = "Heat flow in W"]  
    end
    System(Equation[], t, vars, pars; name)
end


@component function ThermalResistor(; R, name)
    pars = @parameters begin
        R = R
    end

    systems = @named begin
        port_a = HeatPort()
        port_b = HeatPort()
    end

    vars = @variables begin
        Q̇(t), [guess = 0]
        ΔT(t), [guess = 0]
    end    

    equations = Equation[
        ΔT ~ R * Q̇
        ΔT ~ port_a.T - port_b.T
        port_a.Q̇ ~ Q̇
        port_a.Q̇ + port_b.Q̇ ~ 0
    ]
    System(equations, t, vars, pars; name, systems)
end


@component function FixedHeatFlow(; Q̇, name)
    pars = @parameters begin
        Q̇ = Q̇
    end

    systems = @named begin
        port = HeatPort()
    end

    vars = @variables begin
    end

    equations = Equation[
        port.Q̇ ~ -Q̇
    ]
    System(equations, t, vars, pars; name, systems)
end


@component function PrescribedHeatFlow(; name)
    pars = @parameters begin
    end

    systems = @named begin
        port = HeatPort()
    end

    vars = @variables begin
        Q̇(t)
    end

    equations = Equation[
        port.Q̇ ~ -Q̇
    ]
    System(equations, t, vars, pars; name, systems)
end


@component function FixedTemperature(; T, name)
    pars = @parameters begin
        T = T
    end

    systems = @named begin
        port = HeatPort()
    end

    vars = @variables begin
    end

    equations = Equation[
        port.T ~ T
    ]
    System(equations, t, vars, pars; name, systems)
end


@connector function FluidPort(; name)
    pars = @parameters begin
        ϱ
        cₚ
    end

    vars = @variables begin
        p(t), [guess = 1e5, description = "Pressure in Pa"]
        ṁ(t), [guess = 0, connect = Flow, description = "Mass flow rate into the component in kg/s"]
        h(t), [guess = 300*cₚ, connect = Stream, description = "Specific enthalpy in J/kg"] 
    end
    System(Equation[], t, vars, pars; name)
end


@connector function Fluid(; ϱ = 1000, cₚ = 4190, name)
    pars = @parameters begin
        ϱ = ϱ
        cₚ = cₚ
    end

    vars = @variables begin
        ṁ(t), [guess = 0, connect = Flow]
    end

    equations = Equation[
        ṁ ~ 0
    ]
    System(equations, t, vars, pars; name)
end


@component function Pump(; p, name)
    pars = @parameters begin
        p = p
    end

    systems = @named begin
        port = FluidPort()
    end
    
    vars = @variables begin
        ṁ(t), [guess = 0]
        T(t), [guess = 300]
    end
        
    equations = Equation[
        port.ṁ ~ -ṁ
        port.p ~ p
        port.h ~ port.cₚ * T
    ]
    return System(equations, t, vars, pars; name, systems)
end


@component function FluidSink(; name)
    pars = @parameters begin
    end
      
    systems = @named begin
        port = FluidPort()
    end

    vars = @variables begin
    end
    return System(Equation[], t, vars, pars; name, systems)
end


@component function FluidMixer(; n, name)
    pars = @parameters begin
    end

    port_a = [FluidPort(; name=Symbol("port_a$i")) for i in 1:n]
    @named port_b = FluidPort()
    systems = [port_a; port_b]

    vars = @variables begin
        T_b(t), [guess = 300]
    end

    equations = Equation[
        T_b ~ port_b.h / port_b.cₚ
        # momentum balance
        sum([port_a[i].p for i in 1:n])/n ~ port_b.p
        # mass balance
        sum([port_a[i].ṁ for i in 1:n]) + port_b.ṁ ~ 0
        # energy balance
        sum([port_a[i].ṁ * port_a[i].h for i in 1:n]) + port_b.ṁ * port_b.h ~ 0
        [port_a[i].h ~ instream(port_a[i].h) for i in 1:n]
        [domain_connect(port_a[i], port_b) for i in 1:n]
    ]
    System(equations, t, vars, pars; name, systems)
end


function Pipe end

@component function Pipe(; name)
    pars = @parameters begin
    end

    systems = @named begin
        port_a = FluidPort()
        port_b = FluidPort()
        heatPort = HeatPort()
    end

    vars = @variables begin
        T_a(t), [guess = 300]
        T_b(t), [guess = 300]
    end
    
    equations = Equation[
        T_a ~ port_a.h / port_a.cₚ
        T_b ~ port_b.h / port_b.cₚ
        # lumped volume
        heatPort.T ~ (port_a.ṁ >= 0) * T_b + (port_a.ṁ < 0) * T_a
        # momentum balance
        port_a.p ~ port_b.p
        # mass balance
        port_a.ṁ + port_b.ṁ ~ 0
        # energy balance
        port_a.ṁ * port_a.h + heatPort.Q̇ + port_b.ṁ * port_b.h ~ 0
        port_a.h ~ instream(port_a.h)
        port_b.h ~ instream(port_b.h)
        domain_connect(port_a, port_b)
    ]
    System(equations, t, vars, pars; name, systems)
end


@component function HeatExchangerCounterFlow(; kA, name)
    pars = @parameters begin
        kA = kA
    end

    systems = @named begin
        port_11 = FluidPort()
        port_12 = FluidPort()
        port_21 = FluidPort()
        port_22 = FluidPort()
    end

    vars = @variables begin
        Q̇(t), [guess = 0]
        ΔT1(t), [guess = 0]
        ΔT2(t), [guess = 0]
        ΔTm(t)
        T11(t)
        T12(t)
        T21(t)
        T22(t)
    end
    
    equations = Equation[
        # using approximation from Chen1987 for
        # logarithmic mean temperature difference
        ΔT1 ~ T11-T22
        ΔT2 ~ T12-T21
        ΔTm ~ abs((ΔT1 * ΔT2^2 + ΔT1^2 * ΔT2) / 2)^(1/3) * sign(ΔT1)
        T11 ~ port_11.h / port_11.cₚ
        T12 ~ port_12.h / port_12.cₚ
        T21 ~ port_21.h / port_21.cₚ
        T22 ~ port_22.h / port_22.cₚ
        # momentum balance
        port_11.p ~ port_12.p
        port_21.p ~ port_22.p
        # mass balance
        port_11.ṁ + port_12.ṁ ~ 0
        port_21.ṁ + port_22.ṁ ~ 0
        # energy balance
        Q̇ ~ kA * ΔTm
        port_12.h ~ port_11.h - Q̇ / port_11.ṁ 
        port_22.h ~ port_21.h + Q̇ / port_21.ṁ 
        port_11.h ~ instream(port_11.h)
        port_12.h ~ instream(port_12.h)
        port_21.h ~ instream(port_21.h)
        port_22.h ~ instream(port_22.h)        
        domain_connect(port_11, port_12)
        domain_connect(port_21, port_22)        
    ]
    System(equations, t, vars, pars; name, systems)
end


# works both for parallel-flow and counter-flow
@component function HeatExchangerDiscretized(; kA, n = 10, name)
    pars = @parameters begin
        kA = kA
    end

    ports = @named begin
        port_11 = FluidPort()
        port_12 = FluidPort()
        port_21 = FluidPort()
        port_22 = FluidPort()
    end
    pipes_a = [Pipe(; name = Symbol("pipes_a$i")) for i in 1:n]
    pipes_b = [Pipe(; name = Symbol("pipes_b$i")) for i in 1:n]
    wall = [ThermalResistor(; R = n/ParentScope(kA), name = Symbol("wall$i")) for i in 1:n]
    systems = [ports; pipes_a; pipes_b; wall]
    
    vars = @variables begin
        Q̇(t), [guess = 0]
        T11(t)
        T12(t)
        T21(t)
        T22(t)        
    end
    
    equations = Equation[
        T11 ~ port_11.h / port_11.cₚ
        T12 ~ port_12.h / port_12.cₚ
        T21 ~ port_21.h / port_21.cₚ
        T22 ~ port_22.h / port_22.cₚ
        # momentum balance
        port_11.p ~ port_12.p
        port_21.p ~ port_22.p
        # mass balance
        port_11.ṁ + port_12.ṁ ~ 0
        port_21.ṁ + port_22.ṁ ~ 0
        # energy balance
        Q̇ ~ sum([wall[i].Q̇ for i in 1:n])
        port_11.h ~ instream(port_11.h)
        port_12.h ~ instream(port_12.h)
        port_21.h ~ instream(port_21.h)
        port_22.h ~ instream(port_22.h)         
        connect(pipes_a[1].port_a, port_11)
        [connect(pipes_a[i].port_b, pipes_a[i+1].port_a) for i in 1:n-1]      
        connect(pipes_a[n].port_b, port_12)
        connect(pipes_b[1].port_a, port_21)
        [connect(pipes_b[i].port_b, pipes_b[i+1].port_a) for i in 1:n-1]      
        connect(pipes_b[n].port_b, port_22)        
        [connect(pipes_a[i].heatPort, wall[i].port_a) for i in 1:n]        
        [connect(pipes_b[i].heatPort, wall[n+1-i].port_b) for i in 1:n]            
        domain_connect(port_11, port_12)
        domain_connect(port_21, port_22)  
    ]
    System(equations, t, vars, pars; name, systems)
end


@component function HeatPump(; Q̇_0max, η_c, T_c, ΔT, name)
    pars = @parameters begin
        Q̇_0max = Q̇_0max
        η_c = η_c
        T_c = T_c
        ΔT = ΔT
    end

    systems = @named begin
        port_a = FluidPort()
        port_b = FluidPort()
        pipe = Pipe()
        heater = PrescribedHeatFlow()
    end

    vars = @variables begin
        T_0(t)
        Q̇_H(t), [guess = 0]
        Q̇_0(t)
        P(t)
        COP(t)
    end
    
    equations = Equation[
        pipe.T_b ~ pipe.T_a - ΔT
        T_0 ~ (pipe.T_a + pipe.T_b) / 2
        COP ~ T_c / (T_c - T_0) * η_c
        P ~ Q̇_H / COP
        Q̇_H ~ Q̇_0 + P
        heater.Q̇ ~ -Q̇_0
        connect(port_a, pipe.port_a)
        connect(port_b, pipe.port_b)
        connect(pipe.heatPort, heater.port)
    ]
    System(equations, t, vars, pars; name, systems)
end


@component function HeatConsumer(; T_limit = nothing, T_setpoint = nothing, n = nothing, m = nothing, k_smooth = nothing, name)
    pars = @parameters begin
        T_limit = T_limit
        T_setpoint = T_setpoint
        n = n
        m = m
        k_smooth = k_smooth
    end

    systems = @named begin
        pipe = Pipe()
        heater = PrescribedHeatFlow()
        port_a = FluidPort()
        port_b = FluidPort()
    end

    vars = @variables begin
        Q̇(t), [guess = 0]
        T_amb(t)
    end

    equations = Equation[
        Q̇ ~ n + m * (T_setpoint - T_amb) * (1 - tanh(k_smooth * (T_amb - T_limit)))
        heater.Q̇ ~ -Q̇
        connect(port_a, pipe.port_a)
        connect(port_b, pipe.port_b)
        connect(pipe.heatPort, heater.port)
    ]
    System(equations, t, vars, pars; name, systems)
end


@component function HPCRack(; η, name)
    pars = @parameters begin
        η = η
    end

    systems = @named begin
        pipe = Pipe()
        heater = PrescribedHeatFlow()
        port_a = FluidPort()
        port_b = FluidPort()
    end

    vars = @variables begin
        P(t), [guess = 0]
        Q̇(t), [guess = 0]
    end
    
    equations = Equation[
        Q̇ ~ P * η
        heater.Q̇ ~ Q̇
        connect(port_a, pipe.port_a)
        connect(port_b, pipe.port_b)
        connect(pipe.heatPort, heater.port)
    ]
    System(equations, t, vars, pars; name, systems)
end


# Infrastructure model

@component function KKR01(; name)   
    pars = @parameters begin
        η
        fWW # split factor for warm water system
        m0
        m1
        m2
        p0
        p1
        p2
    end

    systems = @named begin
        hpc = HPCRack(η = η)
        fluid = Fluid(ϱ = 1000, cₚ = 4190)
        pump = Pump(p = 1.0)
        sink = FluidSink()
        port_wue01_11 = FluidPort()
        port_wue01_12 = FluidPort()
    end

    vars = @variables begin
        Q̇_pot(t)
        Q̇_cool(t)
        P_pump(t)
    end

    equations = Equation[
        pump.ṁ ~ m0 + m1 * hpc.Q̇ + m2 * hpc.Q̇^2
        Q̇_pot ~ pump.ṁ * (port_wue01_11.h - pump.T*pump.port.cₚ)
        Q̇_cool ~ pump.ṁ * (port_wue01_12.h - pump.T*pump.port.cₚ)
        P_pump ~ p0 + p1 * pump.ṁ + p2 * pump.ṁ^2
        connect(fluid, pump.port)
        connect(pump.port, hpc.port_a)
        connect(hpc.port_b, port_wue01_11)
        connect(port_wue01_12, sink.port)
    ]
    System(equations, t, vars, pars; name, systems)
end


@component function KKR02(; name)      
    pars = @parameters begin
        η
        m0
        m1
        m2
        p0
        p1
        p2
    end

    systems = @named begin
        hpc = HPCRack(η = η)
        fluid = Fluid(ϱ = 1000, cₚ = 4190)
        pump = Pump(p = 1.0)
        sink = FluidSink()
        port_wue03_11 = FluidPort()
        port_wue03_12 = FluidPort()
    end

    vars = @variables begin
        Q̇_pot(t)
        Q̇_cool(t)
        P_pump(t)
    end   

    equations = Equation[
        pump.ṁ ~ m0 + m1 * hpc.Q̇ + m2 * hpc.Q̇^2
        Q̇_pot ~ pump.ṁ * (port_wue03_11.h - pump.T*pump.port.cₚ)
        Q̇_cool ~ pump.ṁ * (port_wue03_12.h - pump.T*pump.port.cₚ)
        P_pump ~ p0 + p1 * pump.ṁ + p2 * pump.ṁ^2
        connect(fluid, pump.port)
        connect(pump.port, hpc.port_a)
        connect(hpc.port_b, port_wue03_11)
        connect(port_wue03_12, sink.port)
    ]
    System(equations, t, vars, pars; name, systems)
end


@component function KKR03(; name)
    pars = @parameters begin
        η
        m0
        m1
        m2
        p0
        p1
        p2        
    end

    systems = @named begin
        hpc = HPCRack(η = η)
        fluid = Fluid(ϱ = 1000, cₚ = 4190)
        pump = Pump(p = 1.0)
        sink = FluidSink()
        port_wue04_11 = FluidPort()
        port_wue04_12 = FluidPort()
    end

    vars = @variables begin
        Q̇_pot(t)
        Q̇_cool(t)
        P_pump(t)
    end 

    equations = Equation[
        pump.ṁ ~ m0 + m1 * hpc.Q̇ + m2 * hpc.Q̇^2
        Q̇_pot ~ pump.ṁ * (port_wue04_11.h - pump.T*pump.port.cₚ)
        Q̇_cool ~ pump.ṁ * (port_wue04_12.h - pump.T*pump.port.cₚ)
        P_pump ~ p0 + p1 * pump.ṁ + p2 * pump.ṁ^2
        connect(fluid, pump.port)
        connect(pump.port, hpc.port_a)
        connect(hpc.port_b, port_wue04_11)
        connect(port_wue04_12, sink.port)
    ]
    System(equations, t, vars, pars; name, systems)
end


@component function KKR04(; name)
    pars = @parameters begin
        η
        fSC # split factor for side cooler system
        m0
        m1
        m2
        p0
        p1
        p2
    end

    systems = @named begin
        hpc = HPCRack(η = η)
        fluid = Fluid(ϱ = 1000, cₚ = 4190)
        pump = Pump(p = 1.0)
        sink = FluidSink()
    end

    vars = @variables begin
        Q̇_cool(t)
        P_pump(t)
    end

    equations = Equation[
        pump.ṁ ~ m0 + m1 * hpc.Q̇ + m2 * hpc.Q̇^2
        Q̇_cool ~ pump.ṁ * (hpc.port_b.h - pump.T*pump.port.cₚ)
        P_pump ~ p0 + p1 * pump.ṁ + p2 * pump.ṁ^2
        connect(fluid, pump.port)
        connect(pump.port, hpc.port_a)
        connect(hpc.port_b, sink.port)
    ]
    System(equations, t, vars, pars; name, systems)
end


@component function K02(; name)
    pars = @parameters begin
        m0
        m1
        m2
        p0
        p1
        p2
        p3
        p4
        r0
        r1
        r2
        r3
    end

    systems = @named begin
    end

    vars = @variables begin
        ṁ(t)
        Q̇_cool(t)
        P_pump(t)
        P_rkw(t)
        T_amb(t)
    end
    
    equations = Equation[
        ṁ ~ m0 + m1 * Q̇_cool + m2 * Q̇_cool^2
        P_pump ~ (p0 + p1 * ṁ + p2 * Q̇_cool *(p3 - T_amb)) * (p4 - ṁ)^2
        P_rkw ~ abs((r0 + r1 * Q̇_cool + r2 * T_amb) * (r3 - T_amb))
    ]
    System(equations, t, vars, pars; name, systems)
end


@component function H01(; name)
    pars = @parameters begin
        kA_wue01
        kA_wue03
        kA_wue04
        m0_wue01
        m1_wue01
        m2_wue01
        m0_wue03
        m1_wue03
        m2_wue03
        m0_wue04
        m1_wue04
        m2_wue04
        m0_hkr01
        m1_hkr01
        m2_hkr01
        m0_hkr02
        m1_hkr02
        m2_hkr02
        m0_abg01
        m1_abg01
        m2_abg01
        p0_hkr
        p1_hkr
        p2_hkr
        p0_wue
        p1_wue
        p2_wue
    end

    systems = @named begin        
        fluid = Fluid(ϱ = 1000, cₚ = 4190)
        wue00 = FluidMixer(n = 3)
        
        pump_wue01 = Pump(p = 1.0)
        wue01 = HeatExchangerDiscretized(kA = kA_wue01)
        port_wue01_11 = FluidPort()
        port_wue01_12 = FluidPort()

        pump_wue03 = Pump(p = 1.0)
        wue03 = HeatExchangerDiscretized(kA = kA_wue03)
        port_wue03_11 = FluidPort()
        port_wue03_12 = FluidPort()

        pump_wue04 = Pump(p = 1.0)
        wue04 = HeatExchangerDiscretized(kA = kA_wue04)
        port_wue04_11 = FluidPort()
        port_wue04_12 = FluidPort()
        
        hkr01 = HeatConsumer()
        hkr02 = HeatConsumer()
        abg01 = HeatConsumer()

        abg02_FL = FluidPort()
        abg02_RL = FluidPort()

        wue00_RL = FluidMixer(n=4)
        sink = FluidSink()
    end

    vars = @variables begin
        Q̇_pot(t), [guess=1]
        P_pump_hkr(t)
        P_pump_wue(t)
        T_amb(t)
    end
    
    equations = Equation[        
        pump_wue01.ṁ ~ m0_wue01 + m1_wue01 * Q̇_pot + m2_wue01 * Q̇_pot^2
        pump_wue01.T ~ wue00_RL.T_b
        connect(pump_wue01.port, wue01.port_21)
        connect(wue01.port_22, wue00.port_a1)
        connect(port_wue01_11, wue01.port_11)
        connect(wue01.port_12, port_wue01_12)  

        pump_wue03.ṁ ~ m0_wue03 + m1_wue03 * Q̇_pot + m2_wue03 * Q̇_pot^2
        pump_wue03.T ~ wue00_RL.T_b
        connect(pump_wue03.port, wue03.port_21)
        connect(wue03.port_22, wue00.port_a2)
        connect(port_wue03_11, wue03.port_11)
        connect(wue03.port_12, port_wue03_12)

        pump_wue04.ṁ ~ m0_wue04 + m1_wue04 * Q̇_pot + m2_wue04 * Q̇_pot^2
        pump_wue04.T ~ wue00_RL.T_b
        connect(pump_wue04.port, wue04.port_21)
        connect(wue04.port_22, wue00.port_a3)
        connect(port_wue04_11, wue04.port_11)
        connect(wue04.port_12, port_wue04_12)

        connect(wue00.port_b, hkr01.port_a, hkr02.port_a, abg01.port_a, abg02_FL)
        connect(wue00.port_b, fluid)       
        
        hkr01.T_amb ~ T_amb
        hkr01.port_a.ṁ ~ m0_hkr01 + m1_hkr01 * hkr01.Q̇ + m2_hkr01 * hkr01.Q̇^2        
        hkr02.T_amb ~ T_amb
        hkr02.port_a.ṁ ~ m0_hkr02 + m1_hkr02 * hkr02.Q̇ + m2_hkr02 * hkr02.Q̇^2        
        abg01.T_amb ~ T_amb
        abg01.port_a.ṁ ~ m0_abg01 + m1_abg01 * abg01.Q̇ + m2_abg01 * abg01.Q̇^2
        connect(hkr01.port_b, wue00_RL.port_a1)
        connect(hkr02.port_b, wue00_RL.port_a2)
        connect(abg01.port_b, wue00_RL.port_a3)
        connect(abg02_RL, wue00_RL.port_a4)
        connect(wue00_RL.port_b, sink.port)

        P_pump_hkr ~ p0_hkr + p1_hkr * (hkr01.port_a.ṁ + hkr02.port_a.ṁ + abg01.port_a.ṁ) + p2_hkr * (hkr01.port_a.ṁ + hkr02.port_a.ṁ + abg01.port_a.ṁ)^2
        P_pump_wue ~ p0_wue + p1_wue * (-wue00.port_b.ṁ) + p2_wue * (-wue00.port_b.ṁ)^2
    ]
    System(equations, t, vars, pars; name, systems)
end


@component function WPG(; name)
    pars = @parameters begin
        Q̇_0max
        η_c
        T_c
        ΔT
    end

    systems = @named begin
        nw_FL = FluidPort()
        nw_RL = FluidPort()
        wpa = HeatPump(Q̇_0max=Q̇_0max, η_c=η_c, T_c=T_c, ΔT=ΔT)
    end

    vars = @variables begin
    end

    equations = Equation[
        connect(nw_FL, wpa.port_a)
        connect(wpa.port_b, nw_RL)
    ]
    System(equations, t, vars, pars; name, systems)
end


@component function Metric(; name)
    pars = @parameters begin
        (LZR_DLR_Racks_AK_HPC_Wirkleistung::DataInterpolations.AbstractInterpolation)(..)
        (LZR_capella_Racks_E12_Wirkleistung::DataInterpolations.AbstractInterpolation)(..)
        (LZR_alpha_Racks_HPC_Wirkleistung::DataInterpolations.AbstractInterpolation)(..)
        (LZR_barnard_Racks_E12_Wirkleistung::DataInterpolations.AbstractInterpolation)(..)
        (LZR_K21_KKR01_B08::DataInterpolations.AbstractInterpolation)(..)
        (LZR_K21_KKR02_B08::DataInterpolations.AbstractInterpolation)(..)
        (LZR_K21_KKR03_B08::DataInterpolations.AbstractInterpolation)(..)
        (LZR_K21_KKR04_B08::DataInterpolations.AbstractInterpolation)(..)
        (LZR_H01_HKR02_B20::DataInterpolations.AbstractInterpolation)(..)
        (LZR_H01_WUE00_B29_LN::DataInterpolations.AbstractInterpolation)(..)
    end

    systems = @named begin
    end

    vars = @variables begin
    end

    System(Equation[], t, vars, pars; name, systems)
end


@component function Infrastructure(; hp_predict=false, name)
    pars = @parameters begin
        hp_predict
    end

    systems = @named begin
        metric = Metric()
        kkr01 = KKR01()
        kkr02 = KKR02()
        kkr03 = KKR03()
        kkr04 = KKR04()
        k02 = K02()
        h01 = H01()
        wpg = WPG()
    end

    vars = @variables begin
    end

    equations = Equation[
        # potential for heat flow to H01, switch between these two equations:
        # - measured data to simulate using real load profile for heat pumps
        # - predict to utilize maximal heat pump usage
        h01.Q̇_pot ~ ifelse(hp_predict==false,
            metric.LZR_H01_WUE00_B29_LN(t),
            min(wpg.wpa.Q̇_0max, kkr01.Q̇_pot + kkr02.Q̇_pot + kkr03.Q̇_pot - h01.hkr01.Q̇ - h01.hkr02.Q̇ - h01.abg01.Q̇))
        
        # residual cooling power
        k02.Q̇_cool ~ kkr01.Q̇_cool + kkr02.Q̇_cool + kkr03.Q̇_cool + kkr04.Q̇_cool

        h01.T_amb ~ metric.LZR_H01_HKR02_B20(t)
        k02.T_amb ~ metric.LZR_H01_HKR02_B20(t)

        kkr01.pump.T ~ metric.LZR_K21_KKR01_B08(t)
        kkr02.pump.T ~ metric.LZR_K21_KKR02_B08(t)
        kkr03.pump.T ~ metric.LZR_K21_KKR03_B08(t)
        kkr04.pump.T ~ metric.LZR_K21_KKR04_B08(t)

        kkr01.hpc.P ~ metric.LZR_DLR_Racks_AK_HPC_Wirkleistung(t) * kkr01.fWW
        kkr02.hpc.P ~ metric.LZR_capella_Racks_E12_Wirkleistung(t)
        kkr03.hpc.P ~ metric.LZR_alpha_Racks_HPC_Wirkleistung(t) + metric.LZR_barnard_Racks_E12_Wirkleistung(t)
        kkr04.hpc.P ~ metric.LZR_DLR_Racks_AK_HPC_Wirkleistung(t) * kkr04.fSC

        connect(kkr01.port_wue01_11, h01.port_wue01_11)
        connect(h01.port_wue01_12, kkr01.port_wue01_12)

        connect(kkr02.port_wue03_11, h01.port_wue03_11)
        connect(h01.port_wue03_12, kkr02.port_wue03_12)

        connect(kkr03.port_wue04_11, h01.port_wue04_11)
        connect(h01.port_wue04_12, kkr03.port_wue04_12)

        # H01.ABG02 only connected to WPG
        # (DLR building heating not used by now)
        connect(h01.abg02_FL, wpg.nw_FL)
        connect(wpg.nw_RL, h01.abg02_RL)
    ]
    System(equations, t, vars, pars; name, systems)
end


# Model initialization and Simulation

function get_operating_point(model::System)
    op = [
        model.hp_predict => false

        model.metric.LZR_DLR_Racks_AK_HPC_Wirkleistung => ConstantInterpolation([1], [1]; extrapolation = ExtrapolationType.Constant)
        model.metric.LZR_capella_Racks_E12_Wirkleistung => ConstantInterpolation([1], [1]; extrapolation = ExtrapolationType.Constant)
        model.metric.LZR_alpha_Racks_HPC_Wirkleistung => ConstantInterpolation([1], [1]; extrapolation = ExtrapolationType.Constant)
        model.metric.LZR_barnard_Racks_E12_Wirkleistung => ConstantInterpolation([1], [1]; extrapolation = ExtrapolationType.Constant)
        model.metric.LZR_K21_KKR01_B08 => ConstantInterpolation([1], [1]; extrapolation = ExtrapolationType.Constant)
        model.metric.LZR_K21_KKR02_B08 => ConstantInterpolation([1], [1]; extrapolation = ExtrapolationType.Constant)
        model.metric.LZR_K21_KKR03_B08 => ConstantInterpolation([1], [1]; extrapolation = ExtrapolationType.Constant)
        model.metric.LZR_K21_KKR04_B08 => ConstantInterpolation([1], [1]; extrapolation = ExtrapolationType.Constant)
        model.metric.LZR_H01_HKR02_B20 => ConstantInterpolation([1], [1]; extrapolation = ExtrapolationType.Constant)
        model.metric.LZR_H01_WUE00_B29_LN => ConstantInterpolation([1], [1]; extrapolation = ExtrapolationType.Constant)

        model.kkr01.η => 0.954
        model.kkr02.η => 0.954
        model.kkr03.η => 0.954
        model.kkr04.η => 0.889

        model.kkr01.fWW => 0.497
        model.kkr04.fSC => (1 - 0.497)
        
        model.kkr01.m0 => 1.1307092339483815
        model.kkr01.m1 => 1.2147249093828569e-5
        model.kkr01.m2 => -6.055450437152e-12
        model.kkr01.p0 => 3.66028810e+02
        model.kkr01.p1 => 2.84176635e+02
        model.kkr01.p2 => 5.75892142e-16

        model.kkr02.m0 => 1.763526676822218
        model.kkr02.m1 => 2.2065174735370812e-5
        model.kkr02.m2 => -9.547651645387452e-12
        model.kkr02.p0 => 471.66972328
        model.kkr02.p1 => 255.84292582
        model.kkr02.p2 => -3.66155406

        model.kkr03.m0 => 5.012761783333329
        model.kkr03.m1 => 9.901857481574788e-6
        model.kkr03.m2 => 2.815978758756067e-12
        model.kkr03.p0 => 1.23250704e+03
        model.kkr03.p1 => 2.37580516e-17
        model.kkr03.p2 => 1.01960474e+01
        
        model.kkr04.m0 => 9.782651374374643
        model.kkr04.m1 => 2.2328393835951993e-5
        model.kkr04.m2 => 3.0607198290076135e-12
        model.kkr04.p0 => 115.08332741
        model.kkr04.p1 => 80.69112287
        model.kkr04.p2 => 7.62014175

        model.k02.m0 => 2.71393510e+01
        model.k02.m1 => 3.78444992e-06
        model.k02.m2 => 2.26610805e-12
        model.k02.p0 => 1.41097983e+01
        model.k02.p1 => 1.52341532e-01
        model.k02.p2 => -1.13412851e-07
        model.k02.p3 => 3.65776845e+02
        model.k02.p4 => -6.03788536e+00
        model.k02.r0 => -2.45614547e+03
        model.k02.r1 => 3.51706686e-04
        model.k02.r2 => 8.32751393e+00
        model.k02.r3 => 2.78301804e+02

        model.h01.kA_wue01 => 150000
        model.h01.kA_wue03 => 150000
        model.h01.kA_wue04 => 150000    
        model.h01.hkr01.T_limit => 286.75242211772184
        model.h01.hkr01.T_setpoint => 287.59210088596194
        model.h01.hkr01.n => 310.0244847966942
        model.h01.hkr01.m => 550.4432668039813
        model.h01.hkr01.k_smooth => 0.6259575967722606
        model.h01.hkr02.T_limit => 218.24399526986969
        model.h01.hkr02.T_setpoint => 1039.2397821495454
        model.h01.hkr02.n => 1298.2896702352907
        model.h01.hkr02.m => 11884.452233719643
        model.h01.hkr02.k_smooth => 0.08083668828138477
        model.h01.abg01.T_limit => -45851.508027480006
        model.h01.abg01.T_setpoint => 360.99009790733055
        model.h01.abg01.n => -435032.48125240003
        model.h01.abg01.m => 3559.3657766540964
        model.h01.abg01.k_smooth => -0.39505084320731954
        model.h01.m0_wue01 => 2.30503182e+00
        model.h01.m1_wue01 => 4.32304496e-06
        model.h01.m2_wue01 => 1.98564411e-12
        model.h01.m0_wue03 => 5.02984388e-12
        model.h01.m1_wue03 => 8.52388839e-09
        model.h01.m2_wue03 => 5.77010143e-12
        model.h01.m0_wue04 => 9.24431462e-20
        model.h01.m1_wue04 => 6.60320753e-06
        model.h01.m2_wue04 => 3.09965656e-12
        model.h01.m0_hkr01 => 1.50073977e-03
        model.h01.m1_hkr01 => 7.79851692e-06
        model.h01.m2_hkr01 => 5.77216381e-11
        model.h01.m0_hkr02 => -2.04958974e-03
        model.h01.m1_hkr02 => 1.46903841e-05
        model.h01.m2_hkr02 => 2.47371713e-10
        model.h01.m0_abg01 => 2.69207086e-01
        model.h01.m1_abg01 => 1.99473838e-05
        model.h01.m2_abg01 => -4.41151156e-11
        model.h01.p0_hkr => 396.36755071
        model.h01.p1_hkr => 153.25670429
        model.h01.p2_hkr => -2.485941
        model.h01.p0_wue => 3.37284516e+02
        model.h01.p1_wue => 6.76835153e+01
        model.h01.p2_wue => -2.37611924e-01

        model.wpg.Q̇_0max => 3*1e6
        model.wpg.η_c => 0.59
        model.wpg.T_c => 90+273.15
        model.wpg.ΔT => 10
    ]

    return op
end


function init_model(df::DataFrame)
    @mtkcompile model = Infrastructure()
    op = get_operating_point(model)
    prob = ODEProblem(model, op, (first(df.t), last(df.t)))
    
    return model, prob, op
end


function simulate(model::System, prob::ODEProblem, df::DataFrame; hp_predict::Bool=false)
    # copy problem and update parameters and data interpolation functions
    prob = remake(prob; tspan=(first(df.t), last(df.t)))
    ps = parameter_values(prob)

    if length(df.t) == 1
        itp_func = ConstantInterpolation
    elseif length(df.t) == 2
        itp_func = LinearInterpolation
    else
        itp_func = PCHIPInterpolation
    end

    p = [
        model.hp_predict,
        model.metric.LZR_DLR_Racks_AK_HPC_Wirkleistung,
        model.metric.LZR_capella_Racks_E12_Wirkleistung,
        model.metric.LZR_alpha_Racks_HPC_Wirkleistung,
        model.metric.LZR_barnard_Racks_E12_Wirkleistung,
        model.metric.LZR_K21_KKR01_B08,
        model.metric.LZR_K21_KKR02_B08,
        model.metric.LZR_K21_KKR03_B08,
        model.metric.LZR_K21_KKR04_B08,
        model.metric.LZR_H01_HKR02_B20,
        model.metric.LZR_H01_WUE00_B29_LN
        ]

    x = [hp_predict,
        itp_func(df."LZR.DLR.Racks-AK.HPC-Wirkleistung", df.t; extrapolation = ExtrapolationType.Constant),
        itp_func(df."LZR.capella.Racks-E12.Wirkleistung", df.t; extrapolation = ExtrapolationType.Constant),
        itp_func(df."LZR.alpha.Racks.HPC-Wirkleistung", df.t; extrapolation = ExtrapolationType.Constant),
        itp_func(df."LZR.barnard.Racks-E12.Wirkleistung", df.t; extrapolation = ExtrapolationType.Constant),
        itp_func(df."LZR.K21.KKR01.B08", df.t; extrapolation = ExtrapolationType.Constant),
        itp_func(df."LZR.K21.KKR02.B08", df.t; extrapolation = ExtrapolationType.Constant),
        itp_func(df."LZR.K21.KKR03.B08", df.t; extrapolation = ExtrapolationType.Constant),
        itp_func(df."LZR.K21.KKR04.B08", df.t; extrapolation = ExtrapolationType.Constant),
        itp_func(df."LZR.H01.HKR02.B20", df.t; extrapolation = ExtrapolationType.Constant),
        itp_func(df."LZR.H01.WUE00.B29.LN", df.t; extrapolation = ExtrapolationType.Constant)
    ]

    setter = setp(prob, p)
    setter(ps, x)

    # run simulation
    sol = solve(prob, QNDF(), saveat=df.t)

    return model, prob, sol
end


# precompile model and ODEProblem
@setup_workload begin
    @compile_workload begin
        @mtkcompile model = Infrastructure()
        op = get_operating_point(model)
        prob = ODEProblem(model, op, (0, 10))
    end
end


end # module
