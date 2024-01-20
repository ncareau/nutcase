from flask import current_app, session
import re           # To break status words
import time         # To format time variables 

from app.api import format_to_text
from app.api import configuration
from app.api import apc_to_nut
from app.api import scrape

#==============================================================================
# Constatnts for GUI
#==============================================================================
Icon_Bat_Charging    = 'bi-battery-charging'
Icon_Bat_Full        = 'bi-battery-full'
Icon_Bat_Half        = 'bi-battery-half'
Icon_Bat_Empty       = 'bi-battery'
Icon_Alert_Triangle  = 'bi-exclamation-triangle'
Icon_Error_Octagon   = 'bi-exclamation-octagon-fill'
Icon_Vin_Boost       = 'bi-chevron-bar-up'
Icon_Vin_Trim        = 'bi-chevron-bar-down'
Icon_Vin_Normal      = 'bi bi-distribute-vertical' # 'bi-chevron-bar-contract'
Icon_Check           = 'bi-check-circle'
Icon_Unknown         = 'bi-question-circle'

Nominal_Width = 75

#==============================================================================
# Prototype HTML blocks for GUI
#==============================================================================
Status_HTML = \
'''
      <div class="d-flex">
        <div class="d-flex flex-fill align-items-center justify-content-end fs-4 main-data"> <!--  justify-content-center -->
          {status_text}
        </div>
        <div class="d-flex px-3 align-items-center">
          <i class="bi bi-plugin fs-3 {line_icon_style}" data-bs-toggle="tooltip" data-bs-placement="right" data-bs-html="true" data-bs-title="{line_icon_tip}"></i>
        </div>
        <div class="d-flex px-3 align-items-center">
          <span class="fs-4"><i class="bi {line_alert_icon} {line_alert_icon_style}" data-bs-toggle="tooltip" data-bs-placement="right" data-bs-html="true" data-bs-title="{line_alert_tip}"></i></span>
        </div>
      </div>
      <div class="d-flex">
        <div class="d-flex flex-fill align-items-center justify-content-end main-data"> <!--  justify-content-center -->
          {secondary_text}
        </div>
        <div class="d-flex px-3 align-items-center">
          <i class="bi {battery_icon} fs-3 {bat_icon_style}" data-bs-toggle="tooltip" data-bs-placement="right" data-bs-html="true" data-bs-title="{bat_icon_tip}"></i>
        </div>
        <div class="d-flex px-3 align-items-center">
          <span class="fs-4"><i class="bi {bat_alert_icon} {bat_alert_style}" data-bs-toggle="tooltip" data-bs-placement="right" data-bs-html="true" data-bs-title="{bat_alert_tip}"></i></span>
        </div>
      </div>
'''

Runtime_HTML = \
'''
<div class="d-flex fs-4 justify-content-center {fmt}">
{time}
</div>
'''

Sounder_HTML = \
'''
<div class="d-flex fs-2 flex-fill justify-content-around">
    <div><i class="bi bi-volume-up-fill main-icon {s_enabled}"></i></div> <!-- style="--bs-text-opacity: .25;"-->
    <div><i class="bi bi-volume-off-fill main-icon {s_muted}"></i></div>
    <div><i class="bi bi-volume-mute-fill main-icon {s_disabled}"></i></div>
</div>
<div class="d-flex flex-fill justify-content-center align-items-center main-data">
    {state}
</div>
'''

Device_Pulldown_HTML = \
'''
<a class="dropdown-item {active}" href="./?addr={addr}&dev={dev}{mode_q}">
    <div class="d-flex align-items-center justify-content-between">
    <div>{addr_name} {dev_name} {mode}</div>
    <div><i class="bi bi-check-circle {def_style}"></i></div>
    </div>
</a>
'''

Download_Pulldown_HTML = \
'''
<a class="dropdown-item" href="/{path}?addr={addr}&download={dl_opt}&dev={dev}{mode_q}">
    {fmt}
</a>
'''

#==============================================================================
# Clean_List - Utility to clean 'null' values from data so that the max 
#   and min functions work
#==============================================================================
def Clean_List( Data ):
    Clean = [x for x in Data if not isinstance(x, str)]
    return Clean

#==============================================================================
# Time_Axis_Array - Make the horizontal time scale axis with labels
#==============================================================================
def Time_Axis_Array( Length ):
    X_Data = []
    for x in range(0, Length):
        if x == 0:
            X_Data.append('Now')
        elif x%10 == 0:
            X_Data.append('-' + str(x/2))
        else:
            X_Data.append('')

    return list(reversed(X_Data))

#===========================================================
# Dougnut graphics - Dougnut_Input_Voltage
#===========================================================
def Dougnut_Input_Voltage( UPS, Result ):
    if Input_Volts := format_to_text.Get_NUT_Variable( UPS, 'input.voltage' ):
        Input_Volts = float(Input_Volts)
    else:
        Input_Volts = 0

    Result['input_volts'] = [ 0, 1 ]
    Result['input_nom'] = [ 0, 0, 1 ] 
    Result['input_scale'] = [ 1, 0, 0, 0, 0 ] 

#===========================================================
# Decide on the max input voltage
    Input_TH = format_to_text.Get_NUT_Variable( UPS, 'input.transfer.high' )
    Line_Nominal = None
    if Input_Nominal := format_to_text.Get_NUT_Variable( UPS, 'input.voltage.nominal' ):
        Line_Nominal = float(Input_Nominal)
    elif Output_Nominal := format_to_text.Get_NUT_Variable( UPS, 'output.voltage.nominal' ):
        Line_Nominal = float(Output_Nominal)

    Max_Input_Volts = 1
    if Input_TH:
        Input_TH = float(Input_TH)
        Max_Input_Volts = Input_TH * 1.1
    elif Line_Nominal:
        Max_Input_Volts = float(Line_Nominal) * 1.22

    if Max_Input_Volts == 0:
        Max_Input_Volts = 1
    if Input_Volts > Max_Input_Volts:
        Input_Volts = Max_Input_Volts
    Result['input_volts'] = [ Input_Volts, Max_Input_Volts - Input_Volts ]

#===========================================================
# Input Voltage scale
    Input_TL = format_to_text.Get_NUT_Variable( UPS, 'input.transfer.low' )
    if Input_TH and Input_TL:
        Input_TL = float(Input_TL)
        Result['input_scale'] = [ 0, 0, Input_TL, Input_TH-Input_TL, Max_Input_Volts-Input_TH  ]
    else:
        Result['input_scale'] = [ 1, 0, 0, 0, 0 ] 

    if Line_Nominal:
        Result['input_nom'] = [ float(Line_Nominal)-(Max_Input_Volts/(Nominal_Width*2)), (Max_Input_Volts/Nominal_Width), Max_Input_Volts-float(Line_Nominal)-(Max_Input_Volts/(Nominal_Width*2)) ]
    else:
        Result['input_nom'] = [ 0, 0, 1 ] 
    return

#===========================================================
# Dougnut graphics - Dougnut_Battery_Charge
#===========================================================
def Dougnut_Battery_Charge( UPS, Result ):
    Result['bat_charge'] = [ 0, 0 ]
    Result['bat_ch_scale'] = [ 1, 0, 0, 0, 0 ]

    if Bat_Charge_Low := format_to_text.Get_NUT_Variable( UPS, 'battery.charge.low' ):
        Bat_Charge_Low = int(Bat_Charge_Low)

    if Bat_Charge_Warn := format_to_text.Get_NUT_Variable( UPS, 'battery.charge.warning' ):
        Bat_Charge_Warn = int(Bat_Charge_Warn)

    if Bat_Charge_Low and Bat_Charge_Warn:
        Result['bat_ch_scale'] = [ 0, 0, int(Bat_Charge_Low), int(Bat_Charge_Warn) - int(Bat_Charge_Low), 100 - int(Bat_Charge_Warn) ]
    elif Bat_Charge_Low and not Bat_Charge_Warn:
        Result['bat_ch_scale'] = [ 0, 0, int(Bat_Charge_Low), 0, 100 - int(Bat_Charge_Low) ]
    elif not Bat_Charge_Low and Bat_Charge_Warn:
        Result['bat_ch_scale'] = [ 0, 0, int(Bat_Charge_Warn), 0, 100 - int(Bat_Charge_Warn) ]

    Bat_Charge = format_to_text.Get_NUT_Variable( UPS, 'battery.charge' )
    if Bat_Charge:
        Bat_Charge = float(Bat_Charge)
        Result['bat_charge'] = [ int(Bat_Charge), 100 - int(Bat_Charge) ]
    return 

#===========================================================
# Dougnut graphics - Dougnut_Battery_Voltage
#===========================================================
def Dougnut_Battery_Voltage( UPS, Result ):
    Result['bat_volts']   = [ 0, 1 ]
    Result['bat_v_scale'] = [ 1, 0, 0, 0, 0 ]
    Result['bat_v_nom']   = [ 0, 0, 0 ]
    
    Bat_Volts_Max = 14.5
    Bat_Volts_Nom = format_to_text.Get_NUT_Variable( UPS, 'battery.voltage.nominal' )
    if Bat_Volts_Nom:
        Bat_Volts_Nom = float(Bat_Volts_Nom)
        Bat_Volts_Max = 1.2 * Bat_Volts_Nom
        Result['bat_v_nom'] = [ float(Bat_Volts_Nom)-(Bat_Volts_Max/(Nominal_Width*2)), (Bat_Volts_Max/Nominal_Width), Bat_Volts_Max-float(Bat_Volts_Nom)-(Bat_Volts_Max/(Nominal_Width*2)) ]

    if Bat_Volts_Low := format_to_text.Get_NUT_Variable( UPS, 'battery.voltage.low' ):
        Bat_Volts_Low = float(Bat_Volts_Low)
        Result['bat_v_scale'] = [ 0, 0, Bat_Volts_Low, (Bat_Volts_Max-Bat_Volts_Low)*0.25, (Bat_Volts_Max-Bat_Volts_Low)*0.75 ]
    else:
        if Bat_Volts_Nom:
            Result['bat_v_scale'] = [ 0, 0, Bat_Volts_Nom*0.82, Bat_Volts_Nom*0.08, Bat_Volts_Nom*0.3 ]

    if Bat_Volts_Max == 0:
        Bat_Volts_Max = 0.1
    if Bat_Volts := format_to_text.Get_NUT_Variable( UPS, 'battery.voltage' ):
        Bat_Volts = float(Bat_Volts)
        Result['bat_volts'] = [ Bat_Volts, Bat_Volts_Max-Bat_Volts ]
    return

#===========================================================
# Dougnut graphics - Dougnut_Output_Power
#===========================================================
def Dougnut_Output_Power( UPS, Result ):
    Result['power_out']       = [ 0, 1, 0 ]
    Result['power_out_scale'] = [ 0, 0, 100, 10 ]
    Power_Watts = '--'

    if UPS_Load := format_to_text.Get_NUT_Variable( UPS, 'ups.load' ):
        UPS_Load = float(UPS_Load)

        Realpower_Nom = format_to_text.Get_NUT_Variable( UPS, 'ups.realpower.nominal' )
        if Server := configuration.Get_Server( current_app, UPS['server_address'] ):
            if 'power' in Server:
                Realpower_Nom = Server['power']
                # current_app.logger.debug("Using power value from config {}".format( Realpower_Nom ))

        if Realpower_Nom:
            Power_Watts = int(float(Realpower_Nom) * (UPS_Load / 100))
        else:
            Power_Watts = 0

        Result['power_out'] = [ int(UPS_Load), 110 - int(UPS_Load), Power_Watts ]
    return

#===========================================================
# Chart graphics - Chart_Input_Voltage
#===========================================================
def Chart_Input_Voltage( UPS, Result ):
    Vin_Y = session['in_volt_y']
    if Input_Volts := format_to_text.Get_NUT_Variable( UPS, 'input.voltage' ):
        Input_Volts = float(Input_Volts)
    else:
        Input_Volts = 0
    # if Input_Volts:
    Vin_Y.append( Input_Volts )
    Vin_Y.pop( 0 )
    Result['in_volt_y'] = Vin_Y
    session['in_volt_y'] = Vin_Y

    #===========================================================
    # Select a minumum range for the Y axis
    #===========================================================
    Result['in_volt_min'] = Result['in_volt_max'] = 'null'

    if current_app.config['UI']['AUTORANGE_VIN']:
        Min_Range = current_app.config['UI']['MIN_RANGE_VIN']
        Data_Max = max(Clean_List(Vin_Y))
        Data_Min = min(Clean_List(Vin_Y))
        Data_Range = Data_Max - Data_Min
        if Data_Range < Min_Range: 
            Pad = (Min_Range - Data_Range) / 2
            if (Data_Min - Pad) < 0:
                Result['in_volt_min'] = 0
                Pad = Pad + (Data_Min - Pad)
            else:
                Result['in_volt_min'] = Data_Min - Pad
            Result['in_volt_max'] = Data_Max + Pad

    return

#===========================================================
# Chart graphics - Chart_Battery_Charge
#===========================================================
def Chart_Battery_Charge( UPS, Result ):
    Charge_Y = session['bat_ch_y']

    if not (Bat_Charge := format_to_text.Get_NUT_Variable( UPS, 'battery.charge' )):
        Bat_Charge = 0

    Bat_Charge = float(Bat_Charge)
    Charge_Y.append( int(Bat_Charge) )
    Charge_Y.pop( 0 )
    Result['bat_ch_y'] = Charge_Y
    session['bat_ch_y'] = Charge_Y
    return

#===========================================================
# Chart graphics - Chart_Output_Power
#===========================================================
def Chart_Output_Power( UPS, Result ):
    Power_Y = session['out_power_y']
    if not (UPS_Load := format_to_text.Get_NUT_Variable( UPS, 'ups.load' )):
        UPS_Load = 0

    UPS_Load = float(UPS_Load)
    Power_Y.append( UPS_Load )
    Power_Y.pop( 0 )
    Result['out_power_y'] = Power_Y
    session['out_power_y'] = Power_Y

    #===========================================================
    # Select a minumum range for the Y axis
    #===========================================================
    Result['out_power_y_min'] = 0
    Result['out_power_y_max'] = 100
    if current_app.config['UI']['AUTORANGE_POW']:
        Min_Range  = current_app.config['UI']['MIN_RANGE_POW']
        Data_Max   = max(Clean_List(Power_Y))
        Data_Min   = min(Clean_List(Power_Y))
        Data_Range = Data_Max - Data_Min
        if Data_Range < Min_Range: 
            Pad = (Min_Range - Data_Range) / 2
            if (Data_Min - Pad) < 0:
                Result['out_power_y_min'] = 0
                Pad = Pad + (Data_Min - Pad)
            else:
                Result['out_power_y_min'] = Data_Min - Pad
            Result['out_power_y_max'] = Data_Max + Pad

    #===========================================================
    # Set Watts scale
    #===========================================================
    Realpower_Nom = format_to_text.Get_NUT_Variable( UPS, 'ups.realpower.nominal' )
    if Server := configuration.Get_Server( current_app, UPS['server_address'] ):
        if 'power' in Server:
            Realpower_Nom = Server['power']
            current_app.logger.debugv("Chart_Output_Power: Using power value from config {}".format( Realpower_Nom ))

    if Realpower_Nom:
        Result['out_power_watts_max'] = int( float(Realpower_Nom) * float(Result['out_power_y_max']) / 100 ) 
        Result['out_power_watts_min'] = int( float(Realpower_Nom) * float(Result['out_power_y_min']) / 100 ) 
    else:
        Result['out_power_watts_max'] = 1
        Result['out_power_watts_min'] = 0

    return

#===========================================================
# Chart graphics - Chart_Runtime
#===========================================================
def Chart_Runtime( UPS, Result ):
    Runtime_Y = session['runtime_y']
    if not (Runtime := format_to_text.Get_NUT_Variable( UPS, 'battery.runtime' )):
        Runtime = 0

    if Runtime:
        Runtime_Y.append( float(Runtime)/60.0 )
        Runtime_Y.pop( 0 )
    Result['runtime_y'] = Runtime_Y
    session['runtime_y'] = Runtime_Y

    if current_app.config['UI']['AUTORANGE_RUN']:
        Min_Range  = current_app.config['UI']['MIN_RANGE_RUN']
        Data_Max   = max(Clean_List(Runtime_Y))
        Data_Min   = min(Clean_List(Runtime_Y))
        Data_Range = Data_Max - Data_Min
        if Data_Range < Min_Range: 
            Pad = (Min_Range - Data_Range) / 2

            if (Data_Min - Pad) < 0:
                Result['runtime_y_min'] = 0
                Pad = Pad + (Data_Min - Pad)
            else:
                Result['runtime_y_min'] = Data_Min - Pad

            Result['runtime_y_max'] = Data_Max + Pad
    return

#==============================================================================
# Process_Runtime_Block - 
#==============================================================================
def Process_Runtime_Block( UPS, Result ):
    if Runtime := format_to_text.Get_NUT_Variable( UPS, 'battery.runtime' ):
        Runtime = float(Runtime)
        Formatted_Time = time.strftime(current_app.config["UI"]["FORMAT_RUNTIME"], time.gmtime( int(Runtime) ))
    else:
        Formatted_Time = 'Not Found'
    
    Runtime_Format = "main-data" 
    if Runtime_Low := format_to_text.Get_NUT_Variable( UPS, 'battery.runtime.low' ):
        if int(Runtime) < int(Runtime_Low):
            Runtime_Format =  "main-data-danger"
    Result['runtime'] = Runtime_HTML.format( time=Formatted_Time, fmt=Runtime_Format )
    return

#==============================================================================
# Process_Sounder_Block - 
#==============================================================================
def Process_Sounder_Block( UPS, Result ):
    Sounder_Text = 'Unknown'
    s_muted = s_disabled = s_enabled = ''
    if Sounder_State := format_to_text.Get_NUT_Variable( UPS, 'ups.beeper.status' ):
        if Sounder_State.lower() == 'enabled':
            Sounder_Text = "Enabled"
            s_enabled = 'active'
        elif Sounder_State.lower() == 'disabled':
            Sounder_Text = "Disabled"
            s_disabled = 'active'
        elif Sounder_State.lower() == 'muted':
            Sounder_Text = "Muted"
            s_muted = 'active'

    #==========================================================================
    # Use ups.beeper.status.text if present (usually only when in APC mode)
    #==========================================================================
    if Beep_Status_Text := format_to_text.Get_NUT_Variable( UPS, 'ups.beeper.status.text' ):
        Sounder_Text = Beep_Status_Text

    Result['sounder'] = Sounder_HTML.format( 
                            state=Sounder_Text, 
                            s_muted= s_muted,
                            s_disabled= s_disabled,
                            s_enabled= s_enabled
                              )
    return

#==============================================================================
# Process_Status_Block - 
#==============================================================================
def Process_Status_Block( UPS, Result ):
    #===========================================================
    # Status block
    Status_Text           = 'Unknown'
    Secondary_Text        = ''
    Line_Icon_Style       = 'text-secondary text-muted'
    Bat_Icon_Style        = 'text-secondary text-muted'
    Battery_Icon          = Icon_Bat_Empty
    Bat_Icon_Style        = 'text-info'
    Battery_Alert_Icon    = Icon_Check
    Bat_Alert_Icon_Style  = 'text-success'
    Line_Alert_Icon       = Icon_Unknown  # Icon_Check
    Line_Alert_Icon_Style = 'text-success'

    Line_Icon_Tip   = 'Line OK'
    Line_Alert_Tip  = 'Line OK'
    Bat_Icon_Tip    = 'Battery OK'
    Bat_Alert_Tip   = 'Battery OK'

    #===========================================================
    # Status block - server ID
    Server = configuration.Get_Server( current_app, UPS['server_address'] )

    if 'name' in Server:
        Server_Name = Server['name']
        Result['server_summary'] = Server_Name + "&nbsp(" + UPS['server_address'] + "&nbsp-&nbsp" + UPS['name'] + ")"
    else:
        Result['server_summary'] = UPS['server_address'] + "&nbsp-&nbsp" + UPS['name']

    #===========================================================
    # Status block
    Status_Var = format_to_text.Get_NUT_Variable( UPS, 'ups.status' )
    if Status_Var:
        Status_Var = Status_Var.upper()
        Search_List = re.split(r' |:|;|-|\.|/|\\', Status_Var )
        current_app.logger.debug("Status message: {}".format( Search_List ))
 
        if 'OL' in Search_List:
            Status_Text = "On-Line"
            Line_Icon_Style = 'text-success'
            Line_Icon_Tip   = 'On-Line, Power OK'
            Line_Alert_Icon_Style = 'text-success'
            Line_Alert_Icon = Icon_Vin_Normal

            Line_Alert_Tip  = 'Voltage Within Limits'
        else:
            Line_Icon_Style = 'text-danger'
            Line_Icon_Tip   = 'Off-Line, Power Missing'

            Line_Alert_Icon_Style = 'text-warning'
            Line_Alert_Icon = Icon_Alert_Triangle
            Line_Alert_Tip = 'Off-Line, Power Missing'

        if 'OB' in Search_List:
            Status_Text = "On-Battery"
            Bat_Icon_Style = 'text-warning'
            Bat_Icon_Tip    = 'On-Battery, Discharging'
        else:
            Bat_Icon_Style = 'text-info'

        if 'CHRG' in Search_List:
            Secondary_Text = "Charging"
            Battery_Icon = Icon_Bat_Charging
            Bat_Icon_Style = 'text-info'
            Bat_Icon_Tip    = 'Battery Charging'
            Bat_Alert_Icon_Style = 'text-Success'
            Battery_Alert_Icon = Icon_Check
            Bat_Alert_Tip    = 'Battery Low, UPS Will Shutdown Soon'
        else:
            if Bat_Charge := format_to_text.Get_NUT_Variable( UPS, 'battery.charge' ):
                Bat_Charge = float(Bat_Charge)
                if Bat_Charge < 50:
                    Bat_Icon_Style = 'text-danger'
                    Battery_Icon = Icon_Bat_Empty
                    Bat_Icon_Tip    = 'Battery Low, UPS Will Shutdown Soon'

                    Bat_Alert_Icon_Style = 'text-warning'
                    Battery_Alert_Icon = Icon_Error_Octagon
                    Bat_Alert_Tip    = 'Battery Low, UPS Will Shutdown Soon'

                    Secondary_Text += "Battery Low"
                elif Bat_Charge < 85:
                    Bat_Icon_Style = 'text-warning'
                    Battery_Icon = Icon_Bat_Half
                    Bat_Icon_Tip    = 'Battery Partially Discharged'
                else:
                    Bat_Icon_Style = 'text-info'
                    Battery_Icon = Icon_Bat_Full
                    Bat_Icon_Tip    = 'Battery Level Good'
                    
        if 'LB' in Search_List:
            Bat_Icon_Style = 'text-danger'
            Battery_Icon = Icon_Bat_Empty
            Bat_Icon_Tip    = 'Battery Low, UPS Will Shutdown Soon'

            Bat_Alert_Icon_Style = 'text-warning'
            Battery_Alert_Icon = Icon_Error_Octagon
            Bat_Alert_Tip = "Low Battery, UPS Will Shutdown Soon"

            Secondary_Text += " Low Battery"

        if 'RB' in Search_List:
            Bat_Icon_Style = 'text-danger'
            Battery_Icon = Icon_Bat_Empty
            Bat_Icon_Tip = "Replace Battery, Battery is EOL"

            Bat_Alert_Icon_Style = 'text-danger'
            Battery_Alert_Icon = Icon_Error_Octagon
            Bat_Alert_Tip = "Replace Battery, Battery is EOL"

            Secondary_Text += " Replace Battery"

        if 'BOOST' in Search_List:
            Line_Alert_Icon_Style = 'text-warning'
            Line_Alert_Icon = Icon_Vin_Boost
            Line_Alert_Tip = "Low Line Level"

            Line_Icon_Style = 'text-warning'
            Line_Icon_Tip = "Low Line Level, Boosting Input"
            Status_Text += " Battery Boosting"

        if 'TRIM' in Search_List:
            Line_Alert_Icon_Style = 'text-warning'
            Line_Alert_Icon = Icon_Vin_Trim
            Line_Alert_Tip = "Line Level High, Trimming Input"

            Line_Icon_Style = 'text-warning'
            Line_Icon_Tip = "Trimming Line Level"
            Status_Text += " Trim Line"

    Result['status'] = Status_HTML.format( 
        status_text=Status_Text,
        line_icon_style=Line_Icon_Style,
        bat_icon_style=Bat_Icon_Style,
        battery_icon=Battery_Icon,
        secondary_text=Secondary_Text,
        line_alert_icon=  Line_Alert_Icon,
        line_alert_icon_style=  Line_Alert_Icon_Style,
        bat_alert_icon=  Battery_Alert_Icon,
        bat_alert_style= Bat_Alert_Icon_Style,
        line_icon_tip= Line_Icon_Tip,
        line_alert_tip= Line_Alert_Tip, 
        bat_icon_tip= Bat_Icon_Tip,
        bat_alert_tip= Bat_Alert_Tip,
    )
    
    #===========================================================
    # Status block drop down
    Result['ups_status'] = Status_Var
    if UPS_Temp := format_to_text.Get_NUT_Variable( UPS, 'ups.temperature' ):
        Result['ups_temp'] = UPS_Temp + "&deg;C"
    else:
        Result['ups_temp'] = "Not Present"

    if APC_Status := format_to_text.Get_NUT_Variable( UPS, 'STATUS' ):
        Result['apc_status'] = APC_Status
    else:
        Result['apc_status'] = "Not Present"

    if APC_BCharge := format_to_text.Get_NUT_Variable( UPS, 'BCHARGE' ):
        Result['apc_bcharge'] = APC_BCharge
    else:
        Result['apc_bcharge'] = "Not Present"

    if APC_StatFlag := format_to_text.Get_NUT_Variable( UPS, 'STATFLAG' ):
        Result['apc_statflag'] = APC_StatFlag
    else:
        Result['apc_statflag'] = "Not Present"

    if UPS_Model := format_to_text.Get_NUT_Variable( UPS, 'ups.model' ):
        Result['ups_model'] = UPS_Model
    else:
        Result['ups_model'] = "Not Present"

    #===========================================================
    # Client list
    if 'clients' in UPS:
        if len(UPS['clients']) == 0 :
            Result['client_cnt'] = 'None'
            Result['client_list'] = '-----'
        else:
            Result['client_cnt'] = len(UPS['clients'])
            Result['client_list'] = ''
            for Client in UPS['clients']:
                Result['client_list'] += Client + "<br>"
    else:
        Result['client_cnt'] = 'None'
        Result['client_list'] = '-----'

    return

#==============================================================================
# Process_Device_Pulldown - 
#==============================================================================
def Process_Device_Pulldown( Addr, Device, Result ):
    Result['device_menu'] = ""

    for d in current_app.config['SERVERS']:
        if 'default' in d:
            Def_Style = ''
        else:
            Def_Style = 'd-none'

        if Addr == d['server'] and Device == d['device']:
            Active_Item = 'active'
        else:    
            Active_Item = ''

        Mode_Query = '&mode=nut'
        Mode_Text  = ' (NUT)'
        if 'mode' in d:
            if d['mode'].lower() == 'apc':
                Mode_Query = '&mode=apc'
                Mode_Text  = ' (APC)'

        if 'name' in d:
            Addr_Name = d['name']
            Dev_Name = ''
        else:
            Addr_Name = d['server']
            Dev_Name = d['device']

        Result['device_menu'] += Device_Pulldown_HTML.format(
            addr      = d['server'],
            dev       = d['device'],
            addr_name = Addr_Name,
            dev_name  = Dev_Name,
            mode      = Mode_Text,
            mode_q    = Mode_Query,
            def_style = Def_Style,
            active    = Active_Item
        )
    return Result

#==============================================================================
# Process_Download_Pulldown - 
#==============================================================================
def Process_Download_Pulldown( UPS, Result, Mode ):
    Result['download_menu'] = ""

    Formats = [ 
        { 'name': 'Metrics',  'path': 'metrics', 'dl_opt': 'false' },
        { 'name': 'JSON',     'path': 'json',    'dl_opt': 'false' },
        { 'name': 'Raw JSON', 'path': 'raw',     'dl_opt': 'false' },
        { 'name': 'HR' },
        { 'name': 'Metrics',  'path': 'metrics', 'dl_opt': 'true'  },
        { 'name': 'JSON',     'path': 'json',    'dl_opt': 'true'  },
        { 'name': 'Raw JSON', 'path': 'raw',     'dl_opt': 'true'  },
    ]

    if Mode == 'apc':
        Mode_q = "&mode={}".format(Mode)
    else:
        Mode_q = ""

    Result['download_menu'] += '<div class="dropdown-item disabled">View</div>'
    for opt in Formats:
        if opt['name'] == "HR":
            Result['download_menu'] += '<div class="dropdown-divider"></div>'
            Result['download_menu'] += '<div class="dropdown-item disabled">Download</div>'
        else:
            Result['download_menu'] += Download_Pulldown_HTML.format(
                path      = opt['path'],
                addr      = UPS['server_address'],
                dev       = UPS['name'],
                mode_q    = Mode_q,
                fmt       = opt['name'],
                dl_opt    = opt['dl_opt'],
                )
    return

#==============================================================================
# Process_Data_For_GUI - 
#==============================================================================
def Process_Data_For_GUI( Scrape_Data, Device ):
    Result = {}

    if Scrape_Data['mode'] == "apc": # scrape.Server_Protocol.APC:
        apc_to_nut.Translate_APC_To_NUT( Scrape_Data )

    #===========================================================
    #  X-Axis & Default stuff
    #===========================================================
    Length = current_app.config['CHART_SAMPLES']
    Result['time_axis_data'] = Time_Axis_Array( Length )
    Result['server_version'] = Scrape_Data['server_version']

    #===========================================================
    # Get the UPS dictionary from the raw structure
    #===========================================================
    UPS = format_to_text.Get_UPS( Scrape_Data, Device )
    if not UPS:
        current_app.logger.warning("Could not find device {} scrape data".format( Device ))
        return {}

    #===========================================================
    # Status block
    #===========================================================
    Process_Download_Pulldown( UPS, Result, Scrape_Data['mode'] )
    Process_Status_Block( UPS, Result )
    Process_Runtime_Block( UPS, Result ) 
    Process_Sounder_Block( UPS, Result )

    #===========================================================
    # Dougnut graphics
    #===========================================================
    Dougnut_Input_Voltage( UPS, Result )
    Dougnut_Battery_Charge( UPS, Result )
    Dougnut_Battery_Voltage( UPS, Result )
    Dougnut_Output_Power( UPS, Result )

    #===========================================================
    # Chart graphics
    #===========================================================
    Chart_Input_Voltage( UPS, Result )
    Chart_Battery_Charge( UPS, Result )
    Chart_Output_Power( UPS, Result )
    Chart_Runtime( UPS, Result )

    return Result

