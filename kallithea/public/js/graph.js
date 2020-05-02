'use strict';

// branch_renderer.js - Rendering of branch DAGs on the client side
//
// Copyright 2010 Marcin Kuzminski <marcin AT python-works DOT com>
// Copyright 2008 Jesper Noehr <jesper AT noehr DOT org>
// Copyright 2008 Dirkjan Ochtman <dirkjan AT ochtman DOT nl>
// Copyright 2006 Alexander Schremmer <alex AT alexanderweb DOT de>
//
// derived from code written by Scott James Remnant <scott@ubuntu.com>
// Copyright 2005 Canonical Ltd.
//
// This software may be used and distributed according to the terms
// of the GNU General Public License, incorporated herein by reference.

var colors = [
	[ 1.0, 0.0, 0.0 ],
	[ 1.0, 1.0, 0.0 ],
	[ 0.0, 1.0, 0.0 ],
	[ 0.0, 1.0, 1.0 ],
	[ 0.0, 0.0, 1.0 ],
	[ 1.0, 0.0, 1.0 ],
	[ 1.0, 1.0, 0.0 ],
	[ 0.0, 0.0, 0.0 ]
];

function BranchRenderer(canvas_id, content_id, row_id_prefix) {
	// canvas_id is canvas to render into
	// content_id's height is applied to canvas
	// row_id_prefix is prefix that is applied to get row id's
	this.canvas = document.getElementById(canvas_id);
	var content = document.getElementById(content_id);

	if (!document.createElement("canvas").getContext)
		this.canvas = window.G_vmlCanvasManager.initElement(this.canvas);
	if (!this.canvas) { // canvas creation did for some reason fail - fail silently
		this.render = function() {};
		return;
	}
	this.ctx = this.canvas.getContext('2d');
	this.ctx.strokeStyle = 'rgb(0, 0, 0)';
	this.ctx.fillStyle = 'rgb(0, 0, 0)';
	this.cur = [0, 0];
	this.line_width = 2.0;
	this.dot_radius = 3.5;
	this.close_x = 1.5 * this.dot_radius;
	this.close_y = 0.5 * this.dot_radius;

	this.calcColor = function(color, bg, fg) {
		color %= colors.length;
		var red = (colors[color][0] * fg) || bg;
		var green = (colors[color][1] * fg) || bg;
		var blue = (colors[color][2] * fg) || bg;
		red = Math.round(red * 255);
		green = Math.round(green * 255);
		blue = Math.round(blue * 255);
		var s = 'rgb(' + red + ', ' + green + ', ' + blue + ')';
		return s;
	}

	this.setColor = function(color, bg, fg) {
		var s = this.calcColor(color, bg, fg);
		this.ctx.strokeStyle = s;
		this.ctx.fillStyle = s;
	}

	this.render = function(data) {
		var idx = 1;
		var canvasWidth = $(this.canvas).parent().width();

		this.canvas.setAttribute('width',canvasWidth);
		this.canvas.setAttribute('height',content.clientHeight);

		// HiDPI version needs to be scaled by 2x then halved via css
		// Note: Firefox on OS X fails scaling if the canvas height is more than 32k
		if (window.devicePixelRatio && content.clientHeight * window.devicePixelRatio < 32768) {
			this.canvas.setAttribute('width', canvasWidth * window.devicePixelRatio);
			this.canvas.setAttribute('height', content.clientHeight * window.devicePixelRatio);
			this.canvas.style.width = canvasWidth + "px";
			this.canvas.style.height = content.clientHeight + "px";
			this.ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
		}

		var lineCount = 1;
		for (let i=0;i<data.length;i++) {
			var in_l = data[i][1];
			for (var j in in_l) {
				var m = in_l[j][0];
				if (m > lineCount)
					lineCount = m;
			}
		}

		var edge_pad = this.dot_radius + 2;
		var box_size = Math.min(18, (canvasWidth - edge_pad * 2) / lineCount);
		var base_x = canvasWidth - edge_pad;

		for (let i=0; i < data.length; ++i) {
			var row = document.getElementById(row_id_prefix+idx);
			if (row == null) {
				console.log("error: row "+row_id_prefix+idx+" not found");
				continue;
			}
			var next = document.getElementById(row_id_prefix+(idx+1));
			var extra = 0;

			const cur = data[i];
			const node = cur[0];
			const in_l = cur[1];
			const closing = cur[2];
			const obsolete_node = cur[3];
			//const bumped_node = cur[4];
			//const divergent_node = cur[5];
			//const extinct_node = cur[6];
			const unstable_node = cur[7];

			// center dots on the first element in a td (not necessarily the first one, but there must be one)
			var firstincell = $(row).find('td>*:visible')[0];
			var nextFirstincell = $(next).find('td>*:visible')[0];
			var rowY = Math.floor(row.offsetTop + firstincell.offsetTop + firstincell.offsetHeight/2);
			var nextY = Math.floor((next == null) ? rowY + row.offsetHeight/2 : next.offsetTop + nextFirstincell.offsetTop + nextFirstincell.offsetHeight/2);

			for (let j in in_l) {
				const line = in_l[j];
				const start = line[0];
				const end = line[1];
				const color = line[2];
				const obsolete_line = line[3];

				const x = Math.floor(base_x - box_size * start);

				// figure out if this is a dead-end;
				// we want to fade away this line
				var dead_end = true;
				if (next != null) {
					const nextdata = data[i+1];
					const next_l = nextdata[1];
					for (var k=0; k < next_l.length; ++k) {
						if (next_l[k][0] == end) {
							dead_end = false;
							break;
						}
					}
					if (nextdata[0][0] == end) // this is a root - not a dead end
						dead_end = false;
				}

				if (dead_end) {
					let gradient = this.ctx.createLinearGradient(x,rowY,x,nextY);
					gradient.addColorStop(0,this.calcColor(color, 0.0, 0.65));
					gradient.addColorStop(1,this.calcColor(color, 1.0, 0.0));
					this.ctx.strokeStyle = gradient;
					this.ctx.fillStyle = gradient;
				}
				// if this is a merge of differently
				// colored line, make it a gradient towards
				// the merged color
				else if (color != node[1] && start == node[0])
				{
					let gradient = this.ctx.createLinearGradient(x,rowY,x,nextY);
					gradient.addColorStop(0,this.calcColor(node[1], 0.0, 0.65));
					gradient.addColorStop(1,this.calcColor(color, 0.0, 0.65));
					this.ctx.strokeStyle = gradient;
					this.ctx.fillStyle = gradient;
				}
				else
				{
					this.setColor(color, 0.0, 0.65);
				}

				this.ctx.lineWidth=this.line_width;
				this.ctx.beginPath();
				if (obsolete_line)
				{
					this.ctx.setLineDash([5]);
				}
				this.ctx.beginPath();
				this.ctx.moveTo(x, rowY);
				if (start == end)
				{
					this.ctx.lineTo(x,nextY+extra,3);
				}
				else
				{
					var x2 = Math.floor(base_x - box_size * end);
					var ymid = (rowY+nextY) / 2;
					if (obsolete_node)
					{
						this.ctx.setLineDash([5]);
					}
					this.ctx.bezierCurveTo (x,ymid,x2,ymid,x2,nextY);
				}
				this.ctx.stroke();
				this.ctx.setLineDash([]); // reset the dashed line, if any
			}

			const column = node[0];
			const color = node[1];

			const x = Math.floor(base_x - box_size * column);

			this.setColor(color, 0.25, 0.75);
			if(unstable_node)
			{
				this.ctx.fillStyle = 'rgb(255, 0, 0)';
			}

			let r = this.dot_radius
			if (obsolete_node)
			{
				this.ctx.beginPath();
				this.ctx.moveTo(x - this.close_x, rowY - this.close_y - 3);
				this.ctx.lineTo(x - this.close_x + 2*this.close_x, rowY - this.close_y + 4*this.close_y - 1);
				this.ctx.moveTo(x - this.close_x, rowY - this.close_y + 4*this.close_y - 1);
				this.ctx.lineTo(x - this.close_x + 2*this.close_x, rowY - this.close_y - 3);
				this.ctx.stroke();
				r -= 0.5
			}
			if (closing)
			{
				this.ctx.fillRect(x - this.close_x, rowY - this.close_y, 2*this.close_x, 2*this.close_y);
			}
			else
			{
				this.ctx.beginPath();
				this.ctx.arc(x, rowY, r, 0, Math.PI * 2, true);
				this.ctx.fill();
			}

			idx++;
		}

	}

}
