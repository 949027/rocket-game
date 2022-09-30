import time
import curses
import asyncio
import uuid
from random import randint, choice
import os
from itertools import cycle

from curses_tools import get_frame_size, draw_frame, read_controls
from obstacles import Obstacle, show_obstacles
from physics import update_speed


TIC_TIMEOUT = 0.1
STARS_AMOUNT = 50
obstacles = []


def get_animation_frames(path):
    animation_frames = []
    for filename in os.listdir(path):
        with open(os.path.join(path, filename), 'r') as file:
            animation_frames.append(file.read())
    return animation_frames


async def sleep(tics=1):
    for _ in range(tics):
        await asyncio.sleep(0)


async def fill_orbit_with_garbage(canvas, frames):
    _, canvas_max_x = canvas.getmaxyx()

    while True:
        for frame in frames:
            frame_size_x, _ = get_frame_size(frame)
            max_row = canvas_max_x - frame_size_x - 2 #todo почему 2?
            coroutines.append(fly_garbage(canvas, column=randint(1, max_row), garbage_frame=frame))
            await sleep(20) #TODO сделать для остальных for


async def fly_garbage(canvas, column, garbage_frame, speed=0.5):
    """Animate garbage, flying from top to bottom. Сolumn position will stay same, as specified on start."""
    rows_number, columns_number = canvas.getmaxyx()

    column = max(column, 0)
    column = min(column, columns_number - 1)

    row = 0

    frame_columns_size, frame_rows_size = get_frame_size(garbage_frame)
    obstacle = Obstacle(row, column, frame_rows_size, frame_columns_size, uuid.uuid1())
    obstacles.append(obstacle)

    try:
        while row < rows_number:
            draw_frame(canvas, row, column, garbage_frame)
            obstacle.row, obstacle.column = row, column
            await asyncio.sleep(0)
            draw_frame(canvas, row, column, garbage_frame, negative=True)
            row += speed
    finally:
        obstacles.remove(obstacle)


async def animate_spaceship(canvas, frames):
    max_row, max_column = [
        coordinate - 1 for coordinate in curses.window.getmaxyx(canvas)
        # -1 т.к. getmaxyx возвращает размеры окна, а не координаты крайних ячеек
    ]
    row = column = 10
    row_speed = column_speed = 0

    for frame in cycle(frames):
        frame_size_x, frame_size_y = get_frame_size(frame)

        for _ in range(2):
            rows_direction, columns_direction, space_pressed = read_controls(canvas)
            row_speed, column_speed = update_speed(row_speed, column_speed, rows_direction, columns_direction)
            target_row = row + rows_direction + row_speed
            target_column = column + columns_direction + column_speed

            if target_row > row:
                row = min(target_row, max_row - frame_size_y)
            elif target_row < row:
                row = max(target_row, 1)

            if target_column > column:
                column = min(target_column, max_column - frame_size_x)
            elif target_column < column:
                column = max(target_column, 1)

            if space_pressed:
                gun_column = column + (frame_size_x / 2)
                coroutines.append(
                    fire(
                        canvas,
                        row,
                        gun_column,
                        rows_speed=-0.3,
                        columns_speed=0
                    )
                )

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

    spaceship_frames = get_animation_frames('animation/spaceship')
    starplace_range_x = (1, window_height - 2)
    starplace_range_y = (1, window_width - 2)
    stars = [
        (randint(*starplace_range_x),
         randint(*starplace_range_y),
         choice('+*.:'))
        for _ in range(STARS_AMOUNT)]

    global coroutines
    coroutines = [
        blink(canvas, row, column, symbol, offset_tics=randint(1, 20))
        for row, column, symbol in stars
    ]

    coroutines.append(animate_spaceship(canvas, spaceship_frames))

    garbage_frames = get_animation_frames('animation/garbage')
    # with open('animation/garbage/trash_large.txt', "r") as garbage_file:
    #     garbage_frame = garbage_file.read()

    coroutines.append(fill_orbit_with_garbage(canvas, garbage_frames))

    coroutines.append(show_obstacles(canvas, obstacles))

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
