class Box(object):
    NORTH = 0
    WEST = 1
    SOUTH = 2
    EAST = 3

    def __init__(self, x: int, y: int, width: int, height: int):
        self.subboxes: list['Box'] = []
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.resizeable = True
        self.draggable = True
        self.parent = None
        self.available_boxes: list[tuple[int, int, int, int, int]] = []  # x1, y1, width, height, angle
        self.current_box: tuple[int, int, int, int, int] = None
        # Target box, dash, allowed own points, allowed remote points
        self.lines: list[tuple['Box', tuple[int, int] or None], list[int], list[int]] = []

        self.prev_x = 0
        self.prev_y = 0
        self.prev_width = 0
        self.prev_height = 0
        self._resizing = None  # boolean: Left, right, up, down
        self._dragging_anchor = None  # x, y

    def _set_view(self, view: 'View'):
        self.view = view
        for box in self.subboxes:
            box._set_view(view)

    def _set_parent(self, parent: 'Box'):
        self.parent = parent
        for box in self.subboxes:
            box._set_parent(self)

    def add_box(self, box: 'Box'):
        self.subboxes.append(box)

    def on_resize(self, width: int, height: int):
        self.width = width
        self.height = height
        self.view.repaint()
        pass

    def on_paint(self, offs_x: int, offs_y: int):
        abs_x = self.x + offs_x
        abs_y = self.y + offs_y
        self.view.canvas.create_rectangle(abs_x, abs_y, abs_x + self.width, abs_y + self.height, fill='green')
        for box in self.subboxes:
            box.on_paint(abs_x, abs_y)
        for line in self.lines:
            point_a = None
            point_b = None
            dir_a = None
            dir_b = None
            dist = None
            for dir1 in line[2]:
                for dir2 in line[3]:
                    x1, y1 = self._get_point(dir1)
                    x2, y2 = line[0]._get_point(dir2)
                    if not dist or dist > (x1 - x2) * (x1 - x2) + (y1 - y2) * (y1 - y2):
                        dist = (x1 - x2) * (x1 - x2) + (y1 - y2) * (y1 - y2)
                        point_a = x1, y1
                        point_b = x2, y2
                        dir_a = dir1
                        dir_b = dir2
            if point_a:
                self._generate_line(point_a, point_b, dir_a, dir_b, line[1])
        pass

    def on_click(self, button: int, x: int, y: int, root_x: int, root_y: int):
        pass

    def on_mouse_move(self, x: int, y: int, root_x: int, root_y: int):
        rel_x = x - self.x
        rel_y = y - self.y

        child = self._get_child_with_drag_focus()
        if child and child != self:
            child.on_mouse_move(rel_x, rel_y, root_x, root_y)
            return

        for box in self.subboxes.__reversed__():
            if box._is_close_to_box(rel_x, rel_y):
                box.on_mouse_move(rel_x, rel_y, root_x, root_y)
                return

        # Resizing
        if self.resizeable and self._is_close_to_box(x, y):
            rad = 8
            # Allow moving of one edge
            left = rel_x < rad
            right = rel_x > self.width - rad
            up = rel_y < rad
            down = rel_y > self.height - rad
            if left or right or up or down:
                self.view.set_cursor("sizing")
                return

        # Moving
        if self.draggable and self._is_in_box(x, y):
            self.view.set_cursor("fleur")
            return

        # All other
        self.view.set_cursor("arrow")

    def on_drag_begin(self, x: int, y: int, root_x: int, root_y: int):
        self.prev_x = self.x
        self.prev_y = self.y
        self.prev_width = self.width
        self.prev_height = self.height
        rel_x = x - self.x
        rel_y = y - self.y

        self._resizing = None
        self._dragging_anchor = None

        for box in self.subboxes.__reversed__():
            if box._is_close_to_box(rel_x, rel_y):
                box.on_drag_begin(rel_x, rel_y, root_x, root_y)
                return

        if self.resizeable and self._is_close_to_box(x, y):
            rad = 8
            # Allow moving of one edge
            left = rel_x < rad
            right = rel_x > self.width - rad
            up = rel_y < rad
            down = rel_y > self.height - rad
            if left or right or up or down:
                self._resizing = (left, right, up, down)
                return
        self._resizing = None

        if self.draggable and self._is_in_box(x, y):
            self._dragging_anchor = rel_x, rel_y
            return
        self._dragging_anchor = None

        pass

    def on_drag_move(self, x: int, y: int, root_x: int, root_y: int, total_dx: int, total_dy: int):
        rel_x = x - self.x
        rel_y = y - self.y
        child = self._get_child_with_drag_focus()
        if child and child != self:
            child.on_drag_move(rel_x, rel_y, root_x, root_y, total_dx, total_dy)
            return

        # Resizing
        if self.resizeable and self._resizing:
            min_width = self.calculate_min_width()
            min_height = self.calculate_min_height()
            left, right, up, down = self._resizing
            boxx, boxy, boxw, boxh, boxrot = self.current_box
            if left:
                if self.prev_width - total_dx < min_width:
                    total_dx = self.prev_width - min_width
                if self.prev_x + total_dx < boxx:
                    total_dx = boxx - self.prev_x
                self.x = self.prev_x + total_dx
                self.width = self.prev_width - total_dx
            elif right:
                if self.prev_width + total_dx < min_width:
                    total_dx = min_width - self.prev_width
                if self.prev_x + self.prev_width + total_dx > boxx + boxw:
                    total_dx = boxx + boxw - self.prev_width - self.prev_x
                self.width = self.prev_width + total_dx
            if up:
                if self.prev_height - total_dy < min_height:
                    total_dy = self.prev_height - min_height
                if self.prev_y + total_dy < boxy:
                    total_dy = boxy - self.prev_y
                self.y = self.prev_y + total_dy
                self.height = self.prev_height - total_dy
            elif down:
                if self.prev_height + total_dy < min_height:
                    total_dy = min_height - self.prev_height
                if self.prev_y + self.prev_height + total_dy > boxy + boxh:
                    total_dy = boxy + boxh - self.prev_height - self.prev_y
                self.height = self.prev_height + total_dy
            self.on_resize(self.width, self.height)

        # Moving
        if self.draggable and self._dragging_anchor:
            anchor_x, anchor_y = self._dragging_anchor
            wanted_x = x - anchor_x
            wanted_y = y - anchor_y
            ret_point, ret_box = self._get_closest_spot_in_available_boxes(wanted_x, wanted_y)
            if ret_point and ret_box:
                # Apply new box, position and rotation
                if (ret_box[4] + self.current_box[4]) % 2 != 0:
                    # We need to rotate
                    backup = self.width
                    self.width = self.height
                    self.height = backup
                self.x, self.y = ret_point
                self.current_box = ret_box
                self.on_resize(self.width, self.height)

    def on_drag_end(self, x: int, y: int, root_x: int, root_y: int, total_dx: int, total_dy: int):
        rel_x = x - self.x
        rel_y = y - self.y

        # Reset drag focus for children
        for box in self.subboxes.__reversed__():
            box.on_drag_end(rel_x, rel_y, root_x, root_y, total_dx, total_dy)

        # Reset all drag focus for self
        self._resizing = None
        self._dragging_anchor = None

    def _is_close_to_box(self, x: int, y: int):
        rad = 8
        return self.x - rad < x < self.x + self.width + rad and self.y - rad < y < self.y + self.height + rad

    def _is_in_box(self, x: int, y: int):
        return self.x < x < self.x + self.width and self.y < y < self.y + self.height

    def calculate_min_width(self):
        return 100

    def calculate_min_height(self):
        return 100

    def abs_x(self):
        if self.parent:
            return self.parent.abs_x() + self.x
        else:
            return self.x

    def abs_y(self):
        if self.parent:
            return self.parent.abs_y() + self.y
        else:
            return self.y

    def _get_child_with_drag_focus(self):
        if self._resizing or self._dragging_anchor:
            return self
        for box in self.subboxes:
            if box._get_child_with_drag_focus():
                return box
        return None

    def _get_available_boxes(self, x: int, y: int) -> list[tuple[int, int, int, int, int]]:
        ret = []
        for bb in self.available_boxes:
            x1, y1, width, height, angle = bb
            if x1 <= x < x1 + width and y1 <= y < y1 + height:
                ret.append(bb)
        return ret

    def _get_closest_spot_in_available_boxes(self, x: int, y: int) \
            -> tuple[tuple[int, int], tuple[int, int, int, int, int]]:  # Closest x and y + box
        dist = -1
        ret_point = None
        ret_box = None
        for box in self.available_boxes:
            local_box = self._get_closest_spot_in_available_box(x, y, box)
            if local_box:
                local_x, local_y, local_width, local_height = local_box
                local_dist = (local_x - x) * (local_x - x) + (local_y - y) * (local_y - y)
                if dist > local_dist or not ret_box:
                    dist = local_dist
                    ret_point = local_x, local_y
                    ret_box = box
        return ret_point, ret_box

    def _get_closest_spot_in_available_box(self, x: int, y: int, box: tuple[int, int, int, int, int]) \
            -> tuple[int, int, int, int]:  # local x, y, width, height
        x1, y1, width, height, angle = box
        if (angle + self.current_box[4]) % 2 == 0:
            # Same effective rotation --> keep width and height
            local_width = self.width
            local_height = self.height
        else:
            # Different rotation -> swap width and height
            local_width = self.height
            local_height = self.width
        # Check if stuff can actually fit
        if local_width > width or local_height > height:
            return None
        # Bound x and y in box
        local_x = x
        local_y = y
        if local_x > x1 + width - local_width:
            local_x = x1 + width - local_width
        if local_x < x1:
            local_x = x1
        if local_y > y1 + height - local_height:
            local_y = y1 + height - local_height
        if local_y < y1:
            local_y = y1

        return local_x, local_y, local_width, local_height

    def _get_point(self, direction: int) -> tuple[int, int]:
        if direction == Box.NORTH:
            return self.abs_x() + self.width / 2, self.abs_y()
        elif direction == Box.SOUTH:
            return self.abs_x() + self.width / 2, self.abs_y() + self.height
        elif direction == Box.WEST:
            return self.abs_x(), self.abs_y() + self.height / 2
        elif direction == Box.EAST:
            return self.abs_x() + self.width, self.abs_y() + self.height / 2

    def _generate_line(self, point_a: tuple[int, int], point_b: tuple[int, int], dir_a: int, dir_b: int,
                       dash: tuple[int, int] or None):
        shortest = 20
        points = []
        current = self._walk_point(point_a, dir_a, shortest)
        target = self._walk_point(point_b, dir_b, shortest)
        directions_possible = [dir_a]
        for i in range(0, 4):
            if not i == dir_a and not i == self._opposite_dir(dir_a):
                directions_possible.append(i)

        points.append(point_a[0])
        points.append(point_a[1])
        points.append(current[0])
        points.append(current[1])

        while current[0] != target[0] or current[1] != target[1]:
            current_dir = None
            for next_dir in directions_possible:
                if self._is_good_direction(current, target, next_dir):
                    current_dir = next_dir
                    break
            if current_dir is None:
                # We have not found a correct direction yet, which probably means that we need to do an 180
                # (by turning in an allowed direction and walking some steps)
                current_dir = directions_possible[0]
                steps = shortest
            else:
                steps = self._get_recommended_steps(current, target, current_dir, dir_b)
            current = self._walk_point(current, current_dir, steps)
            points.append(current[0])
            points.append(current[1])

            directions_possible = []
            # Only allow left/right
            for i in range(0, 4):
                if not i == current_dir and not i == self._opposite_dir(current_dir):
                    directions_possible.append(i)

        points.append(point_b[0])
        points.append(point_b[1])

        self.view.canvas.create_line(points, dash=dash)

    def _walk_point(self, point: tuple[int, int], direction: int, pixels: int) -> tuple[int, int]:
        if direction == Box.NORTH:
            return point[0], point[1] - pixels
        elif direction == Box.SOUTH:
            return point[0], point[1] + pixels
        elif direction == Box.WEST:
            return point[0] - pixels, point[1]
        elif direction == Box.EAST:
            return point[0] + pixels, point[1]

    def _is_good_direction(self, point: tuple[int, int], target: tuple[int, int], direction: int) -> bool:
        if direction == Box.NORTH:
            return point[1] > target[1]
        elif direction == Box.SOUTH:
            return point[1] < target[1]
        elif direction == Box.WEST:
            return point[0] > target[0]
        elif direction == Box.EAST:
            return point[0] < target[0]

    def _get_recommended_steps(self, point: tuple[int, int], target: tuple[int, int], direction: int,
                               target_dir: int) -> int:
        if direction == Box.NORTH:
            # Finish if possible
            if point[0] == target[0] and target_dir != Box.NORTH:
                return point[1] - target[1]
            # If we end up in a good spot at least, go until that exact coordinate too
            if (target_dir == Box.EAST and target[0] < point[0]) or (target_dir == Box.WEST and target[0] > point[0]) \
                    or target_dir == Box.NORTH:
                return point[1] - target[1]
            # Else we only take half the steps required to then go another way
            return int((point[1] - target[1]) / 2)
        elif direction == Box.SOUTH:
            # Finish if possible
            if point[0] == target[0] and target_dir != Box.SOUTH:
                return target[1] - point[1]
            # If we end up in a good spot at least, go until that exact coordinate too
            if (target_dir == Box.EAST and target[0] < point[0]) or (target_dir == Box.WEST and target[0] > point[0]) \
                    or target_dir == Box.SOUTH:
                return target[1] - point[1]
            # Else we only take half the steps required to then go another way
            return int((target[1] - point[1]) / 2)
        elif direction == Box.WEST:
            # Finish if possible
            if point[1] == target[1] and target_dir != Box.WEST:
                return point[0] - target[0]
            # If we end up in a good spot at least, go until that exact coordinate too
            if (target_dir == Box.SOUTH and target[1] < point[1]) or (
                    target_dir == Box.NORTH and target[1] > point[1]) \
                    or target_dir == Box.WEST:
                return point[0] - target[0]
            # Else we only take half the steps required to then go another way
            return int((point[0] - target[0]) / 2)
        elif direction == Box.EAST:
            # Finish if possible
            if point[1] == target[1] and target_dir != Box.EAST:
                return target[0] - point[0]
            # If we end up in a good spot at least, go until that exact coordinate too
            if (target_dir == Box.SOUTH and target[1] < point[1]) or (
                    target_dir == Box.NORTH and target[1] > point[1]) \
                    or target_dir == Box.EAST:
                return target[0] - point[0]
            # Else we only take half the steps required to then go another way
            return int((target[0] - point[0]) / 2)

    def _opposite_dir(self, direction: int) -> int:
        if direction == Box.NORTH:
            return Box.SOUTH
        elif direction == Box.WEST:
            return Box.EAST
        elif direction == Box.SOUTH:
            return Box.NORTH
        elif direction == Box.EAST:
            return Box.WEST
