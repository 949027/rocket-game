import time
import curses
import asyncio
from random import randint, choice
import os
from itertools import cycle


TIC_TIMEOUT = 0.1
STARS_AMOUNT = 50

SPACE_KEY_CODE = 32
LEFT_KEY_CODE = 260
RIGHT_KEY_CODE = 261
UP_KEY_CODE = 259
DOWN_KEY_CODE = 258


def get_frame_size(frame):
    lines = frame.splitlines()
    size_y = len(lines)
    size_x = len(max(lines))
    return size_x, size_y


def read_controls(canvas):
    """Read keys pressed and returns tuple witl controls state."""

    rows_direction = columns_direction = 0
    space_pressed = False

    curses.window.nodelay(canvas, True)

    while True:
        pressed_key_code = canvas.getch()

        if pressed_key_code == -1:
            # https://docs.python.org/3/library/curses.html#curses.window.getch
            break

        if pressed_key_code == UP_KEY_CODE:
            rows_direction = -10

        if pressed_key_code == DOWN_KEY_CODE:
            rows_direction = 10

        if pressed_key_code == RIGHT_KEY_CODE:
            columns_direction = 10

        if pressed_key_code == LEFT_KEY_CODE:
            columns_direction = -10

        if pressed_key_code == SPACE_KEY_CODE:
            space_pressed = True

    return rows_direction, columns_direction, space_pressed


def draw_frame(canvas, start_row, start_column, text, negative=False):
    """Draw multiline text fragment on canvas, erase text instead of
    drawing if negative=True is specified."""
    rows_number, columns_number = canvas.getmaxyx()

    for row, line in enumerate(text.splitlines(), round(start_row)):
        if row < 0:
            continue

        if row >= rows_number:
            break

        for column, symbol in enumerate(line, round(start_column)):
            if column < 0:
                continue

            if column >= columns_number:
                break

            if symbol == ' ':
                continue

            # Check that current position it is not in a lower right corner of the window
            # Curses will raise exception in that case. Don`t ask why???
            # https://docs.python.org/3/library/curses.html#curses.window.addch
            if row == rows_number - 1 and column == columns_number - 1:
                continue

            symbol = symbol if not negative else ' '
            canvas.addch(row, column, symbol)


def get_animation_frames(path):
    animation_frames = []
    for filename in os.listdir(path):
        with open(os.path.join(path, filename), 'r') as file:
            animation_frames.append(file.read())
    return animation_frames


async def animate_spaceship(canvas, frames):
    max_row, max_column = [
        coordinate - 1 for coordinate in curses.window.getmaxyx(canvas)
        # -1 ??.??. getmaxyx ???????????????????? ?????????????? ????????, ?? ???? ???????????????????? ?????????????? ??????????
    ]
    row = max_row / 2
    column = max_column / 2

    for frame in cycle(frames):
        frame_size_x, frame_size_y = get_frame_size(frame)

        for _ in range(2):
            rows_direction, columns_direction, space_pressed = read_controls(canvas)
            target_row = row + rows_direction
            target_column = column + columns_direction

            if rows_direction > 0:
                row = min(target_row, max_row - frame_size_y)
            elif rows_direction < 0:
                row = max(target_row, 1)

            if columns_direction > 0:
                column = min(target_column, max_column - frame_size_x)
            elif columns_direction < 0:
                column = max(target_column, 1)

            draw_frame(canvas, row, column, frame)
            await asyncio.sleep(0)
            draw_frame(canvas, row, column, frame, True)


async def blink(canvas, row, column, symbol, offset_tics):
    while True:
        for _ in range(offset_tics):
            await asyncio.sleep(0)

        canvas.addstr(row, column, symbol, curses.A_DIM)
        for _ in range(20):
            await asyncio.sleep(0)

        canvas.addstr(row, column, symbol)
        for _ in range(3):
            await asyncio.sleep(0)

        canvas.addstr(row, column, symbol, curses.A_BOLD)
        for _ in range(5):
            await asyncio.sleep(0)

        canvas.addstr(row, column, symbol)
        for _ in range(3):
            await asyncio.sleep(0)


async def fire(canvas, start_row, start_column, rows_speed=-0.3, columns_speed=0):
    """Display animation of gun shot, direction and speed can be specified."""

    row, column = start_row, start_column

    canvas.addstr(round(row), round(column), '*')
    await asyncio.sleep(0)

    canvas.addstr(round(row), round(column), 'O')
    await asyncio.sleep(0)
    canvas.addstr(round(row), round(column), ' ')

    row += rows_speed
    column += columns_speed

    symbol = '-' if columns_speed else '|'

    rows, columns = canvas.getmaxyx()
    max_row, max_column = rows - 1, columns - 1

    curses.beep()

    while 0 < row < max_row and 0 < column < max_column:
        canvas.addstr(round(row), round(column), symbol)
        await asyncio.sleep(0)
        canvas.addstr(round(row), round(column), ' ')
        row += rows_speed
        column += columns_speed


def draw(canvas):
    curses.curs_set(False)
    canvas.border()
    window_height, window_width = curses.window.getmaxyx(canvas)

    frames = get_animation_frames('animation')
    starplace_range_x = (1, window_height - 2)
    starplace_range_y = (1, window_width - 2)
    stars = [
        (randint(*starplace_range_x),
         randint(*starplace_range_y),
         choice('+*.:'))
        for _ in range(STARS_AMOUNT)]

    coroutines = [
        blink(canvas, row, column, symbol, offset_tics=randint(1, 20))
        for row, column, symbol in stars
    ]
    coroutines.append(
        fire(
            canvas,
            window_height / 2,
            window_width / 2,
            rows_speed=-0.3,
            columns_speed=0
        )
    )
    coroutines.append(animate_spaceship(canvas, frames))

    while True:
        for coroutine in coroutines:
            try:
                coroutine.send(None)
            except StopIteration:
                coroutines.remove(coroutine)

        canvas.refresh()
        time.sleep(TIC_TIMEOUT)


def main():
    curses.update_lines_cols()
    curses.wrapper(draw)


if __name__ == '__main__':
    main()
