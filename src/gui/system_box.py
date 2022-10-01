from gui.box import Box


class SystemBox(Box):
    INTERFACE_BAR_HEIGHT = 40
    INTERFACE_BAR_BORDER = 10
    MIN_INNER_WIDTH = 80
    MIN_INNER_HEIGHT = 80
    INTERFACE_WIDTH = 100

    def __init__(self, x: int, y: int, width: int, height: int):
        super().__init__(x, y, width, height)
        self.interface_boxes: list[Box] = []
        self.inner_boxes: list[Box] = []

    def add_interface_box(self, box: Box, place: bool):
        self.interface_boxes.append(box)
        box.available_bounding_boxes.append(self.recalculate_box(0, (0, 0, 0, 0, Box.NORTH)))
        box.available_bounding_boxes.append(self.recalculate_box(1, (0, 0, 0, 0, Box.WEST)))
        box.available_bounding_boxes.append(self.recalculate_box(2, (0, 0, 0, 0, Box.SOUTH)))
        box.available_bounding_boxes.append(self.recalculate_box(3, (0, 0, 0, 0, Box.EAST)))
        box.resizeable = False
        if place:
            box.x = SystemBox.INTERFACE_BAR_HEIGHT
            box.y = 0
            box.width = SystemBox.INTERFACE_WIDTH
            box.height = SystemBox.INTERFACE_BAR_HEIGHT
            box.current_box = box.available_bounding_boxes[0]
        box.allowed_directions = []
        self.recalculate_interface_box(box)
        box.on_change_orientation = lambda i: self.recalculate_interface_box(box)
        self.add_box(box)

    def add_inner_box(self, box: Box):
        if not box.x or box.x < SystemBox.INTERFACE_BAR_HEIGHT:
            box.x = SystemBox.INTERFACE_BAR_HEIGHT
        if not box.y or box.y < SystemBox.INTERFACE_BAR_HEIGHT:
            box.y = SystemBox.INTERFACE_BAR_HEIGHT
        box.available_bounding_boxes.append(self.recalculate_box(0, (0, 0, 0, 0, -1)))
        self.add_box(box)

    def on_resize(self, width: int, height: int):
        # Move all inner boxes pre-resize
        for box in self.subboxes:
            ind = box.get_drag_box_index()
            for i in range(0, len(box.available_bounding_boxes)):
                box.available_bounding_boxes[i] = self.recalculate_box(i, box.available_bounding_boxes[i])
                if ind == i:
                    x, y, _, _ = box.get_closest_spot_in_available_box(box.x, box.y, box.available_bounding_boxes[i])
                    box.x = x
                    box.y = y
        # Resize
        super(SystemBox, self).on_resize(width, height)

    def recalculate_box(self, ind: int, box: tuple[int, int, int, int, int]):
        x, y, width, height, angle = box
        if angle == -1:
            b = SystemBox.INTERFACE_BAR_HEIGHT + SystemBox.INTERFACE_BAR_BORDER
            x = b
            y = b
            width = self.width - b * 2
            height = self.height - b * 2
        elif angle == Box.NORTH or angle == Box.SOUTH:
            x = SystemBox.INTERFACE_BAR_HEIGHT
            width = self.width - SystemBox.INTERFACE_BAR_HEIGHT * 2
            if angle == Box.NORTH:
                y = 0
            else:
                y = self.height - SystemBox.INTERFACE_BAR_HEIGHT
            height = SystemBox.INTERFACE_BAR_HEIGHT
        else:
            y = SystemBox.INTERFACE_BAR_HEIGHT
            height = self.height - SystemBox.INTERFACE_BAR_HEIGHT * 2
            if angle == Box.WEST:
                x = 0
            else:
                x = self.width - SystemBox.INTERFACE_BAR_HEIGHT
            width = SystemBox.INTERFACE_BAR_HEIGHT
        for subbox in self.subboxes:
            if subbox.get_drag_box_index() == ind:
                subbox.x += x - box[0]
                subbox.y += y - box[1]
        return x, y, width, height, angle

    def recalculate_interface_box(self, box: Box):
        # Recalculates the possible outgoing directions
        ind = box.get_drag_box_index()
        if ind:
            bounding_box = box.available_bounding_boxes[ind]
            if len(box.allowed_directions) == 0:
                box.allowed_directions.append(ind)
                box.reapply_line_directions()
            elif box.allowed_directions[0] == ind:
                return  # nothing to do
            else:
                box.allowed_directions = [ind]
                box.reapply_line_directions()

    def calculate_min_width(self):
        b = SystemBox.INTERFACE_BAR_HEIGHT
        max_width_child = SystemBox.MIN_INNER_WIDTH
        for x in self.inner_boxes:
            if x.width > max_width_child:
                max_width_child = x.width
        return b * 2 + max(max_width_child + 2 * SystemBox.INTERFACE_BAR_BORDER, SystemBox.INTERFACE_WIDTH)

    def calculate_min_height(self):
        b = SystemBox.INTERFACE_BAR_HEIGHT
        max_height_child = SystemBox.MIN_INNER_HEIGHT
        for x in self.inner_boxes:
            if x.height > max_height_child:
                max_height_child = x.height
        return b * 2 + max(max_height_child + 2 * SystemBox.INTERFACE_BAR_BORDER, SystemBox.INTERFACE_WIDTH)
