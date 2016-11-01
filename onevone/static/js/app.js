$(function(){
	var champions = {}
	
	var keyCodes = {
		UP_ARROW: 38,
		DOWN_ARROW: 40,
		ENTER: 13,
		ESCAPE: 27,
		TAB: 9
	}

	var AutoComplete = function(options) {
		options = options || {}
		this.pool = options.pool || []
		this.matches = []
		this.selectedIndex = 0
		this.currentVal = options.currentVal || ''
		this.maxResults = options.maxResults || 4
		this.renderParams = options.renderParams || {}
	}

	AutoComplete.prototype.update = function(val) {
		this.matches = []
		if(val != this.currentVal && val.length >= 2) {
			for(var i = 0; i < this.pool.length; i++) {
				if(this.matches.length >= this.maxResults) break
				if(this.pool[i].toLowerCase().match(val.toLowerCase()) != null) {
					this.matches.push(this.pool[i])
				}
			}
			this.matches.sort(function(a, b) {
				return b.indexOf(val) - a.indexOf(val)
			})
			this.currentVal = val			
		}
		if(this.render)
			this.render(this.renderParams)
	};

	AutoComplete.prototype.selectPrevious = function() {
		if(this.matches.length == 0) return
		this.selectedIndex = this.selectedIndex - 1 < 0 ? this.matches.length - 1 : 
											    		  this.selectedIndex - 1
		if(this.render)
			this.render(this.renderParams)
	},
	AutoComplete.prototype.selectNext = function() {
		if(this.matches.length == 0) return
		this.selectedIndex = this.selectedIndex + 1 >= this.matches.length ? 0 : 
											           this.selectedIndex + 1
        if(this.render)
			this.render(this.renderParams)

	},
	AutoComplete.prototype.reset = function(options) {
		options = options || {}
		this.matches = []
		this.selectedIndex = 0
		this.currentVal = options.newVal || ''
		if(this.render)
			this.render(this.renderParams)
		this.renderParams = options.renderParams || this.renderParams
	}
	AutoComplete.prototype.getSelected = function() {
		if(this.matches.length < 1) return null
		return this.matches[this.selectedIndex]
	}


	function render(options) {
		if(!options.$element || !options.$input) return
		var $element = options.$element
		var $input = options.$input
		$element.html('')
		var self = this
		this.matches.forEach(function(match, index){
			var champMatch = champions[match]
			var $itemContent = $('<span></span>').html(champMatch.name)
			var $itemImage = $('<div></div>')
								.addClass('champion-icon big c' + champMatch.id)
			var itemClass = index == self.selectedIndex ? 'autocomplete-item selected' :
											    		  'autocomplete-item'
			var $item = $('<div></div>')
							.addClass(itemClass)
							.append($itemImage)
							.append($itemContent)
							.data('value', champMatch.name)
							.click(function(event) {
								console.log($(this).data('value'))
								$input.val($(this).data('value'))
								self.reset()
							});

			$element.append($item)
		})		
	}

	function initialize(argument) {
		
		var autoComplete = new AutoComplete({
			pool: Object.keys(champions).sort()
		})
		autoComplete.render = render;
		
		$('input.autocompleted').each(function(index, el) {
			var $this = $(this)
			var $elem = $this.siblings('.autocomplete-container')
							 .children('.autocomplete-results')
			$this.focus(function(event) {
				autoComplete.reset({
					newVal: $this.val(),
					renderParams: {
						$element: $elem,
						$input:	$this,
					} 
				})
			});

			$this.on('input', function(event) {
				autoComplete.update($this.val())
			});

			$this.keydown(function(event) {
				if(!event.keyCode in keyCodes) return

				switch(event.keyCode) {
				case keyCodes.DOWN_ARROW:
					autoComplete.selectNext()
					event.preventDefault()
					break
				case keyCodes.UP_ARROW:
					autoComplete.selectPrevious()
					event.preventDefault()
					break
				case keyCodes.ENTER:
					var selection = autoComplete.getSelected()
					if(!selection) return
					$this.val(selection)
					autoComplete.reset()
					break
				case keyCodes.ESCAPE:
					autoComplete.reset()
					break
				default:
					return
				}
			});	
		});

		$('a#find-matchup').click(function(event) {
			event.preventDefault()
			var champion = $('.input-container #champion').val()
			var enemy = $('.input-container #enemy').val()
			if(champion.length < 1 || enemy.length < 1) return
			window.location.href = '/matchup/' + champion + '/' + enemy
		});

	}
	$.get('/api/v0/champions', function(payload) {
		payload.data.forEach(function(champion, index) {
			champions[champion.name] = champion
			if(index == payload.data.length - 1) {
				initialize()
			} 
		})
	});
})