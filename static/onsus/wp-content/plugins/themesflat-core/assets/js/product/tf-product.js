;(function($) {

    "use strict";

    var productsOwl = function($scope) {
        if ( $().owlCarousel ) {
            $scope.find('.tf-products.has-carousel').each(function(){
                var
                $this = $(this),
                item = $this.data("column"),
                item2 = $this.data("column2"),
                item3 = $this.data("column3"),
                spacer = Number($this.data("spacer")),
                prev_icon = $this.data("prev_icon"),
                next_icon = $this.data("next_icon");

                var loop = false;
                if ($this.data("loop") == 'yes') {
                    loop = true;
                }

                var arrow = false;
                if ($this.data("arrow") == 'yes') {
                    arrow = true;
                } 

                var bullets = false;
                if ($this.data("bullets") == 'yes') {
                    bullets = true;
                }

                var auto = false;
                if ($this.data("auto") == 'yes') {
                    auto = true;
                }  

                $this.find('.owl-carousel').owlCarousel({
                    loop: loop,
                    margin: spacer,
                    nav: arrow,
                    dots: bullets,
                    autoplay: auto,
                    autoplayTimeout: 5000,
                    smartSpeed: 850,
                    autoplayHoverPause: true,
                    navText : ["<i class=\""+prev_icon+"\"></i>","<i class=\""+next_icon+"\"></i>"],
                    responsive: {
                        0:{
                            items:item3
                        },
                        500:{
                            items:item3
                        },
                        768:{
                            items:item2
                        },
                        1100:{
                            items:item2
                        },
                        1366:{
                            items:item
                        }
                    }
                });

            });
        }
    } 

    var tf_countdown = function(){
        $('.tf-countdown').each(function(){
            var endDate = $(this).data('date');
            $(this).countdown( endDate, function(event) {
                var start_format = '<div class="countdown-inner">';
                // if(event.offset.days > 0) {  
                    var format_day =  '<div class="countdown-day"><div class="time"><strong>%D</strong></div><div class="text">Days</div></div>';
                    var format_hour = '<div class="countdown-hour"><div class="time"><strong>%H</strong></div><div class="text">Hours</div></div>';
                    var format_min = '<div class="countdown-min"><div class="time"><strong>%M</strong></div><div class="text">Mins</div></div>';
                    var format_sec = '<div class="countdown-sec"><div class="time"><strong>%S</strong></div><div class="text">Secs</div></div>';
                    
                    var end_format = '</div>'; 
                    $(this).html(event.strftime(start_format +  format_day + format_hour + format_min + format_sec + end_format));
                // }
            });
        });
        // $(".tf-products .item ").each(function(){
        //     var height2 = $(this).outerHeight(true);
        //     $(this).children('.ounner').css("height", height2);
        // });
    }

    var product_Carousel_row = function($scope) {
        $(window).on('load ',function() {

            // $scope.find('.tf-products.multirow.has-carousel').each(function(){
                $(".product-test").each(function(index, element){
                    var $this = $(this);
                    $this.addClass("instance-" + index);
                    $this.find(".swiper-button-prev").addClass("btn-prev-" + index);
                    $this.find(".swiper-button-next").addClass("btn-next-" + index);
                    var row = $this.data("row"),
                        item4 = $this.data("column4"),
                        item1 = $this.data("column"),
                        item2 = $this.data("column2"),
                        item3 = $this.data("column3");
                    var swiper = new Swiper(".instance-" + index, {
                        loop:false,
                        slidesPerColumnFill: 'row',
                        slidesPerColumn: row,
                        observer: true,
                        observeParents: true,
                        spaceBetween: 15,
                        pagination: {
                            el: '.swiper-pagination',
                            clickable: true,
                        },
                        navigation: {
                            nextEl: '.swiper-button-next',
                            prevEl: '.swiper-button-prev',
                        },
                        breakpoints: {
                            0: {
                                slidesPerView: item4,
                                slidesPerColumn: row,
                                observer: true,
                                observeParents: true,
                                spaceBetween: 15,
                            },
                            500: {
                                slidesPerView: item3,
                                slidesPerColumn: row,
                                observer: true,
                                observeParents: true,
                                spaceBetween: 15,
                            },
                            767: {
                                slidesPerView: item2,
                                slidesPerColumn: row,
                                observer: true,
                                observeParents: true,
                                spaceBetween: 15,
                            },
                            1200: {
                                slidesPerView: item1,
                                slidesPerColumn: row,
                                observer: true,
                                observeParents: true,
                                spaceBetween: 15,
                            },
                        },
                        // nextButton: ".btn-next-" + index,
                        // prevButton: ".btn-prev-" + index
                    });
                });
            // });
       
        });
    }

    var productOptions = function () { 
        $('.product-option .thumb').on('click', function (e) {

            if ($(this).hasClass('active')) {
                e.preventDefault;
            } else {
                $(this).parent().find(".thumb.active").each(function () {
                    $(this).removeClass('active');
                });
                $(this).addClass('active');
                var options_img = $(this).data("src");

                $(this).closest('.item').find('.img_thumbnail').removeClass('none animated slideInRight').fadeOut(200, function () {
                    $(this).attr('src', options_img);
                    $(this).addClass('animated slideInRight').fadeIn(100);
                });
            }
        });

    }




    $(window).on('elementor/frontend/init', function() {
        elementorFrontend.hooks.addAction( 'frontend/element_ready/tfposts.default', productsOwl );
        elementorFrontend.hooks.addAction( 'frontend/element_ready/tfposts.default', tf_countdown );
        elementorFrontend.hooks.addAction( 'frontend/element_ready/tfproductmulti.default', productOptions );
        elementorFrontend.hooks.addAction( 'frontend/element_ready/tfposts.default', productOptions );
        elementorFrontend.hooks.addAction( 'frontend/element_ready/tfproductmulti.default', tf_countdown );

        // elementorFrontend.hooks.addAction( 'frontend/element_ready/tfproductmulti.default', product_Carousel_row );


    });

})(jQuery);
