import pcbnew
import wx
import os
import math

class CoilDialog(wx.Dialog):
    def __init__(self, parent):
        super(CoilDialog, self).__init__(parent, title="Rectangle PCB Coil Generator", size=(450, 470))
        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)
        grid = wx.FlexGridSizer(8, 2, 10, 10)
        self.inputs = {}

        def add_input(label, default_val, key):
            lbl = wx.StaticText(panel, label=label)
            txt = wx.TextCtrl(panel, value=str(default_val))
            grid.Add(lbl, 0, wx.ALIGN_CENTER_VERTICAL)
            grid.Add(txt, 1, wx.EXPAND)
            self.inputs[key] = txt

        add_input("Bottom-Left X (mm):", 100.0, 'x')
        add_input("Bottom-Left Y (mm):", 100.0, 'y')
        add_input("Outer Width (mm):", 50.0, 'width')
        add_input("Outer Height (mm):", 50.0, 'height')
        add_input("Turns per side:", 5, 'turns')
        add_input("Track Width (mm):", 0.6, 'track_width')
        add_input("Track Spacing (mm):", 0.4, 'spacing')
        add_input("Chamfer Distance (mm) [0=None]:", 0.0, 'chamfer')

        lbl_terminals = wx.StaticText(panel, label="Terminals Position:")
        self.terminals_cb = wx.ComboBox(panel, choices=["Inner", "Outer"], style=wx.CB_READONLY)
        self.terminals_cb.SetSelection(0)
        grid.Add(lbl_terminals, 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self.terminals_cb, 1, wx.EXPAND)

        vbox.Add(grid, 1, wx.ALL | wx.EXPAND, 15)

        btn_box = wx.BoxSizer(wx.HORIZONTAL)
        ok_btn = wx.Button(panel, label="Generate")
        ok_btn.Bind(wx.EVT_BUTTON, self.on_ok)
        cancel_btn = wx.Button(panel, label="Cancel")
        cancel_btn.Bind(wx.EVT_BUTTON, self.on_cancel)
        btn_box.Add(ok_btn, 0, wx.ALL, 5)
        btn_box.Add(cancel_btn, 0, wx.ALL, 5)

        vbox.Add(btn_box, 0, wx.ALIGN_CENTER | wx.BOTTOM, 10)
        panel.SetSizer(vbox)

    def on_ok(self, event):
        self.EndModal(wx.ID_OK)

    def on_cancel(self, event):
        self.EndModal(wx.ID_CANCEL)

    def get_values(self):
        return {
            'x': float(self.inputs['x'].GetValue()),
            'y': float(self.inputs['y'].GetValue()),
            'width': float(self.inputs['width'].GetValue()),
            'height': float(self.inputs['height'].GetValue()),
            'turns': int(self.inputs['turns'].GetValue()),
            'track_width': float(self.inputs['track_width'].GetValue()),
            'spacing': float(self.inputs['spacing'].GetValue()),
            'chamfer': float(self.inputs['chamfer'].GetValue()),
            'terminals': self.terminals_cb.GetStringSelection()
        }

class RectangleCoilPlugin(pcbnew.ActionPlugin):
    def defaults(self):
        self.name = "Rectangle PCB Coil Generator"
        self.category = "Generate PCB geometry"
        self.description = "Generates a two-layer rectangular spiral coil grouped together"
        self.show_toolbar_button = True
        plugin_dir = os.path.dirname(__file__)
        self.icon_file_name = os.path.join(plugin_dir, 'icon_light.png')
        self.dark_icon_file_name = os.path.join(plugin_dir, 'icon_dark.png')

    def Run(self):
        board = pcbnew.GetBoard()
        dlg = CoilDialog(None)
        if dlg.ShowModal() == wx.ID_OK:
            vals = dlg.get_values()
            self.generate_coil(board, vals)
        dlg.Destroy()

    def generate_coil(self, board, vals):
        pitch = vals['track_width'] + vals['spacing']
        terminals_mode = vals['terminals'].lower()

        group = pcbnew.PCB_GROUP(board)
        board.Add(group)

        def to_iu(mm): return int(mm * 1e6)

        def add_track(x1, y1, x2, y2, layer):
            track = pcbnew.PCB_TRACK(board)
            track.SetStart(pcbnew.VECTOR2I(to_iu(x1), to_iu(y1)))
            track.SetEnd(pcbnew.VECTOR2I(to_iu(x2), to_iu(y2)))
            track.SetWidth(to_iu(vals['track_width']))
            track.SetLayer(layer)
            board.Add(track)
            group.AddItem(track)

        def add_via(x, y):
            via = pcbnew.PCB_VIA(board)
            via.SetPosition(pcbnew.VECTOR2I(to_iu(x), to_iu(y)))
            via.SetWidth(to_iu(0.6))
            via.SetDrill(to_iu(0.3))
            board.Add(via)
            group.AddItem(via)

        def generate_spiral(layer, center_x, center_y, outer_w, outer_h, turns, pitch, chamfer, is_bottom, is_inner_terminals):
            points = []
            left = center_x - outer_w / 2.0
            right = center_x + outer_w / 2.0
            top = center_y - outer_h / 2.0
            bottom = center_y + outer_h / 2.0

            if is_bottom:
                left += pitch / 2.0
                right -= pitch / 2.0
                top += pitch / 2.0
                bottom -= pitch / 2.0

            spiral_inward = True
            if is_inner_terminals:
                if not is_bottom: spiral_inward = False
                else: spiral_inward = True
            else:
                if not is_bottom: spiral_inward = True
                else: spiral_inward = False

            if spiral_inward:
                for t in range(turns):
                    p1_x = left + chamfer if t == 0 else left + chamfer + t*pitch
                    p1_y = bottom - t*pitch
                    p2_x = right - chamfer - t*pitch
                    p2_y = bottom - t*pitch
                    p3_x = right - t*pitch
                    p3_y = bottom - chamfer - t*pitch
                    p4_x = right - t*pitch
                    p4_y = top + chamfer + t*pitch
                    p5_x = right - chamfer - t*pitch
                    p5_y = top + t*pitch
                    p6_x = left + chamfer + (t+1)*pitch
                    p6_y = top + t*pitch
                    p7_x = left + (t+1)*pitch
                    p7_y = top + chamfer + t*pitch
                    p8_x = left + (t+1)*pitch
                    p8_y = bottom - chamfer - (t+1)*pitch
                    p9_x = left + chamfer + (t+1)*pitch
                    p9_y = bottom - (t+1)*pitch

                    if chamfer == 0:
                        points.extend([(p1_x, p1_y), (p2_x, p2_y), (p4_x, p4_y), (p6_x, p6_y)])
                        if t == turns - 1:
                            points.append((p8_x, bottom - (t+1)*pitch))
                    else:
                        points.extend([(p1_x, p1_y), (p2_x, p2_y), (p3_x, p3_y), (p4_x, p4_y), 
                                       (p5_x, p5_y), (p6_x, p6_y), (p7_x, p7_y), (p8_x, p8_y), (p9_x, p9_y)])
            else:
                temp_points = []
                for t in range(turns):
                    c_tl = chamfer + pitch if chamfer > 0 else 0

                    p1_x = left + t*pitch
                    p1_y = bottom - chamfer - t*pitch
                    p2_x = left + t*pitch
                    p2_y = top + c_tl + t*pitch
                    p3_x = left + c_tl + t*pitch
                    p3_y = top + t*pitch
                    p4_x = right - chamfer - t*pitch
                    p4_y = top + t*pitch
                    p5_x = right - t*pitch
                    p5_y = top + chamfer + t*pitch
                    p6_x = right - t*pitch
                    p6_y = bottom - chamfer - t*pitch
                    p7_x = right - chamfer - t*pitch
                    p7_y = bottom - t*pitch
                    p8_x = left + chamfer + (t+1)*pitch
                    p8_y = bottom - t*pitch
                    p9_x = left + (t+1)*pitch
                    p9_y = bottom - chamfer - (t+1)*pitch

                    if chamfer == 0:
                        if t == 0: temp_points.append((left, bottom))
                        temp_points.extend([(left + t*pitch, top + t*pitch), 
                                            (right - t*pitch, top + t*pitch),
                                            (right - t*pitch, bottom - t*pitch),
                                            (left + (t+1)*pitch, bottom - t*pitch)])
                    else:
                        if t == 0: temp_points.append((left, bottom - chamfer))
                        temp_points.extend([(p2_x, p2_y), (p3_x, p3_y), (p4_x, p4_y),
                                            (p5_x, p5_y), (p6_x, p6_y), (p7_x, p7_y),
                                            (p8_x, p8_y), (p9_x, p9_y)])
                points = list(reversed(temp_points))
            return points

        center_x = vals['x'] + vals['width'] / 2.0
        center_y = vals['y'] - vals['height'] / 2.0
        is_inner = (terminals_mode == 'inner')

        pts_top = generate_spiral(pcbnew.F_Cu, center_x, center_y, vals['width'], vals['height'], 
                                  vals['turns'], pitch, vals['chamfer'], False, is_inner)
        pts_bot = generate_spiral(pcbnew.B_Cu, center_x, center_y, vals['width'], vals['height'], 
                                  vals['turns'], pitch, vals['chamfer'], True, is_inner)

        for i in range(len(pts_top) - 1): add_track(pts_top[i][0], pts_top[i][1], pts_top[i+1][0], pts_top[i+1][1], pcbnew.F_Cu)
        for i in range(len(pts_bot) - 1): add_track(pts_bot[i][0], pts_bot[i][1], pts_bot[i+1][0], pts_bot[i+1][1], pcbnew.B_Cu)

        if len(pts_top) > 0 and len(pts_bot) > 0:
            center_top = pts_top[-1]
            center_bot = pts_bot[0]

            via_dia = 0.6
            target_dist = (vals['track_width'] / 2.0) + vals['spacing'] + (via_dia / 2.0)

            if not is_inner:
                via_pos_x = center_top[0] + pitch
                via_pos_y = center_top[1]

            else:
                last_seg_dx = pts_top[-1][0] - pts_top[-2][0]
                last_seg_dy = pts_top[-1][1] - pts_top[-2][1]

                seg_len = math.hypot(last_seg_dx, last_seg_dy)
                if seg_len > 0:
                    dir_x = last_seg_dx / seg_len
                    dir_y = last_seg_dy / seg_len
                else:
                    dir_x, dir_y = -1, 0

                via_pos_x = center_top[0] + dir_x * target_dist
                via_pos_y = center_top[1] + dir_y * target_dist

            add_track(center_top[0], center_top[1], via_pos_x, via_pos_y, pcbnew.F_Cu)
            add_track(center_bot[0], center_bot[1], via_pos_x, via_pos_y, pcbnew.B_Cu)
            add_via(via_pos_x, via_pos_y)

        pcbnew.Refresh()
